from __future__ import annotations

import json
import re
from typing import Any, Callable

from app.core.constants import LLM_TEMPERATURE_LOW, LLM_TOKEN_UPPER_LIMIT
from app.domains.analysis_assistant.file_store import load_file
from app.domains.analysis_assistant.prompts import build_tool_results_followup_user_prompt
from app.domains.analysis_assistant.tools import (
    FilterClause,
    crosstab,
    describe_numeric,
    freq,
    read_csv_bytes,
    sample_text_responses,
)
from app.infrastructure.llm.client import LLMClient


DEFAULT_FREQ_TOP_K = 20
DEFAULT_SAMPLE_TEXT_N = 25
MAX_TOOL_CALLS_PER_TURN = 3

# Providers/gateways may truncate aggressively; keep a healthy per-turn output cap.
ASSISTANT_MAX_OUTPUT_TOKENS_FLOOR = 4096


_TOOL_JSON_RE = re.compile(r"\{\s*\"tool_calls\"\s*:\s*\[.*?\]\s*\}", re.DOTALL)


def _extract_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extract a minimal tool_calls JSON object from model text (best-effort)."""

    if "```" in text:
        for block in re.findall(
            r"```(?:json)?\s*(.*?)\s*```",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            block = block.strip()
            if "\"tool_calls\"" in block:
                try:
                    obj = json.loads(block)
                    calls = obj.get("tool_calls")
                    return calls if isinstance(calls, list) else []
                except Exception:
                    pass

    m = _TOOL_JSON_RE.search(text)
    if not m:
        return []

    try:
        obj = json.loads(m.group(0))
        calls = obj.get("tool_calls")
        return calls if isinstance(calls, list) else []
    except Exception:
        return []


def _parse_filters(raw: Any) -> list[FilterClause] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("filters must be a list")

    out: list[FilterClause] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each filter must be an object")
        out.append(
            FilterClause(
                column=str(item.get("column")),
                op=str(item.get("op")) if item.get("op") is not None else "eq",
                value=str(item.get("value")),
            )
        )
    return out


def _run_tool(df, tool: dict[str, Any]) -> dict[str, Any]:
    name = str(tool.get("name") or "")
    args = tool.get("args") or {}
    if not isinstance(args, dict):
        raise ValueError("tool args must be an object")

    filters = _parse_filters(args.get("filters"))

    if name == "freq":
        return freq(
            df,
            column=str(args.get("column")),
            filters=filters,
            top_k=int(args.get("top_k") or DEFAULT_FREQ_TOP_K),
        )
    if name == "crosstab":
        return crosstab(
            df,
            row=str(args.get("row")),
            col=str(args.get("col")),
            filters=filters,
        )
    if name == "describe_numeric":
        return describe_numeric(
            df,
            column=str(args.get("column")),
            filters=filters,
        )
    if name == "sample_text":
        return sample_text_responses(
            df,
            column=str(args.get("column")),
            filters=filters,
            n=int(args.get("n") or DEFAULT_SAMPLE_TEXT_N),
            redact=bool(args.get("redact") if args.get("redact") is not None else True),
        )

    raise ValueError(f"Unknown tool: {name}")


def make_invoke_llm_with_tools_node(llm: LLMClient) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Invoke the LLM; optionally run one tool round if requested.

    This repo's LLM abstraction doesn't expose native tool calling, so we use a
    minimal text-based tool request format described in the system prompt.
    """

    def _invoke(state: dict[str, Any]) -> dict[str, Any]:
        messages = state.get("messages") or []
        # Give the assistant enough budget to produce multi-section answers.
        # (Some providers/gateways may truncate aggressively; a higher cap helps.)
        max_tokens = max(LLM_TOKEN_UPPER_LIMIT, ASSISTANT_MAX_OUTPUT_TOKENS_FLOOR)
        text = (
            llm.invoke_llm(
                messages,
                max_output_tokens=max_tokens,
                temperature=LLM_TEMPERATURE_LOW,
            )
            or ""
        ).strip()

        tool_calls = _extract_tool_calls(text)
        if not tool_calls:
            out_messages = list(messages)
            out_messages.append({"role": "assistant", "content": text})
            return {
                "messages": out_messages,
                "assistant_message": text,
                "insights": text,
            }

        file_id = (state.get("active_file_id") or "").strip()
        if not file_id:
            out_messages = list(messages)
            out_messages.append({"role": "assistant", "content": text})
            return {
                "messages": out_messages,
                "assistant_message": text,
                "insights": text,
            }

        df = read_csv_bytes(load_file(file_id))

        tool_results: list[dict[str, Any]] = []
        for call in tool_calls[:MAX_TOOL_CALLS_PER_TURN]:
            try:
                tool_results.append(_run_tool(df, call))
            except Exception as e:
                tool_results.append({"type": "tool_error", "error": str(e), "call": call})

        followup_messages = list(messages)
        # Preserve the model's tool request turn for debugging/memory.
        followup_messages.append({"role": "assistant", "content": text})

        tool_results_json = json.dumps(tool_results, ensure_ascii=False)
        followup_messages.append(
            {
                "role": "user",
                "content": build_tool_results_followup_user_prompt(
                    tool_results_json=tool_results_json
                ),
            }
        )

        final_text = llm.invoke_llm(
            followup_messages,
            max_output_tokens=max_tokens,
            temperature=LLM_TEMPERATURE_LOW,
        )
        out_messages = list(followup_messages)
        out_messages.append({"role": "assistant", "content": final_text})
        return {
            "messages": out_messages,
            "assistant_message": final_text,
            "insights": final_text,
        }

    return _invoke
