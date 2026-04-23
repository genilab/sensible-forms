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

# Guardrail: don't let the model ask for an unbounded number of expensive tool calls.
# (This is per "tool round".)
MAX_TOOL_CALLS_PER_TURN = 5

# Allow a small number of iterative tool rounds in a single user turn so tool_calls
# don't leak into the user-facing response.
MAX_TOOL_ROUNDS_PER_TURN = 2

# Providers/gateways may truncate aggressively; keep a healthy per-turn output cap.
ASSISTANT_MAX_OUTPUT_TOKENS_FLOOR = 4096


# We support a minimal tool-calling protocol via plain text.
# The model is instructed to emit a JSON object like:
#   {"tool_calls": [{"name": "freq", "args": {...}}, ...]}
# This regex is intentionally permissive and best-effort.
_TOOL_JSON_RE = re.compile(r"\{\s*\"tool_calls\"\s*:\s*\[.*?\]\s*\}", re.DOTALL)
_TOOL_FENCED_BLOCK_RE = re.compile(
    r"```(?:json)?\s*.*?\"tool_calls\".*?```",
    flags=re.DOTALL | re.IGNORECASE,
)


def _strip_tool_protocol(text: str) -> str:
    """Remove any embedded tool-calling protocol from user-visible text."""

    if not text:
        return ""

    cleaned = _TOOL_FENCED_BLOCK_RE.sub("", text)
    cleaned = _TOOL_JSON_RE.sub("", cleaned)
    return cleaned.strip()


def _extract_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extract tool call requests embedded in model text.

    This implementation is deliberately tolerant:
    - If the model wraps JSON in fenced code blocks, we prefer parsing those.
    - Otherwise we fall back to a regex match for a JSON object containing `tool_calls`.

    If parsing fails, we treat it as "no tool calls" and just return the model text.
    """

    # Prefer fenced JSON blocks to reduce false positives.
    if "```" in text:
        for block in re.findall(
            r"```(?:json)?\s*(.*?)\s*```",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            block = block.strip()
            if '"tool_calls"' in block:
                try:
                    obj = json.loads(block)
                    calls = obj.get("tool_calls")
                    return calls if isinstance(calls, list) else []
                except Exception:
                    # If one code block doesn't parse, keep searching.
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
    """Parse optional `filters` args into typed `FilterClause` objects."""

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
    """Dispatch a single tool call onto deterministic Python functions.

    These tools operate on the uploaded dataset (a pandas DataFrame) and return
    JSON-serializable dictionaries that are safe to send back to the LLM.

    This is the main "hybrid" pattern in this domain:
    - LLM decides *what* it wants computed
    - Python tools compute exact numbers
    - LLM uses tool outputs to write the final narrative answer
    """

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
        # Accept both the canonical arg names (row/col) and common model variants
        # (row_column/col_column) to keep tool calls resilient.
        row = args.get("row") if args.get("row") is not None else args.get("row_column")
        col = args.get("col") if args.get("col") is not None else args.get("col_column")
        return crosstab(
            df,
            row=str(row),
            col=str(col),
            filters=filters,
        )
    if name == "describe_numeric":
        return describe_numeric(
            df,
            column=str(args.get("column")),
            filters=filters,
        )
    if name == "sample_text":
        # Default to redaction to reduce the risk of leaking sensitive free-text.
        return sample_text_responses(
            df,
            column=str(args.get("column")),
            filters=filters,
            n=int(args.get("n") or DEFAULT_SAMPLE_TEXT_N),
            redact=bool(args.get("redact") if args.get("redact") is not None else True),
        )

    raise ValueError(f"Unknown tool: {name}")


def make_invoke_llm_with_tools_node(llm: LLMClient) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a LangGraph node that invokes the LLM and optionally runs tools.

    Why this exists:
    - The current `LLMClient` abstraction does not expose provider-native tool calling.
    - Instead, we implement a small "tool request" protocol via JSON in the model output.

    Behavioral contract:
    - If the model does NOT request tools: return its text directly.
    - If the model requests tools AND a dataset is available: run up to N tools, then
      send tool outputs back to the model for a final answer.
    - If the model requests tools but there's no dataset: fall back to returning the text.
    """

    def _invoke(state: dict[str, Any]) -> dict[str, Any]:
        # `build_messages` constructs this list; checkpointing keeps it across turns.
        messages = state.get("messages") or []

        # Tool calls only make sense when a dataset is active.
        file_id = (state.get("active_file_id") or "").strip()

        # Give the assistant enough budget to produce multi-section answers.
        # (Some providers/gateways may truncate aggressively; a higher cap helps.)
        max_tokens = max(LLM_TOKEN_UPPER_LIMIT, ASSISTANT_MAX_OUTPUT_TOKENS_FLOOR)

        out_messages = list(messages)

        def _call_llm(current_messages):
            return (
                llm.invoke_llm(
                    current_messages,
                    max_output_tokens=max_tokens,
                    temperature=LLM_TEMPERATURE_LOW,
                )
                or ""
            ).strip()

        # First pass: ask the model to answer OR emit a tool request.
        text = _call_llm(out_messages)

        df = None
        tool_rounds = 0

        while True:
            tool_calls = _extract_tool_calls(text)

            if not tool_calls:
                # Normal chat response: ensure we don't leak internal tool-call JSON.
                clean_text = _strip_tool_protocol(text)
                out_messages.append({"role": "assistant", "content": clean_text})
                return {
                    "messages": out_messages,
                    "assistant_message": clean_text,
                    "insights": clean_text,
                }

            if not file_id:
                # No dataset is available; strip the internal protocol and return something user-facing.
                clean_text = _strip_tool_protocol(text)
                if not clean_text:
                    clean_text = (
                        "I can compute exact statistics once a CSV is uploaded. "
                        "Upload the dataset and ask again."
                    )
                out_messages.append({"role": "assistant", "content": clean_text})
                return {
                    "messages": out_messages,
                    "assistant_message": clean_text,
                    "insights": clean_text,
                }

            if tool_rounds >= MAX_TOOL_ROUNDS_PER_TURN:
                # Safety stop: don't loop forever. Return the best user-visible text we have.
                clean_text = _strip_tool_protocol(text)
                if not clean_text:
                    clean_text = (
                        "I wasn't able to finish computing the requested statistics in this response. "
                        "Could you ask for 1–2 specific statistics at a time?"
                    )
                out_messages.append({"role": "assistant", "content": clean_text})
                return {
                    "messages": out_messages,
                    "assistant_message": clean_text,
                    "insights": clean_text,
                }

            if df is None:
                # Load and parse the uploaded CSV into a DataFrame once per turn.
                # Note: read_csv_bytes enforces a conservative max row limit.
                df = read_csv_bytes(load_file(file_id))

            # Run tools deterministically in Python.
            tool_results: list[dict[str, Any]] = []
            for call in tool_calls[:MAX_TOOL_CALLS_PER_TURN]:
                try:
                    tool_results.append(_run_tool(df, call))
                except Exception as e:
                    tool_results.append({"type": "tool_error", "error": str(e), "call": call})

            # Preserve the model's tool-request turn for checkpoint memory/debugging.
            out_messages.append({"role": "assistant", "content": text})

            tool_results_json = json.dumps(tool_results, ensure_ascii=False)
            out_messages.append(
                {
                    "role": "user",
                    "content": build_tool_results_followup_user_prompt(
                        tool_results_json=tool_results_json
                    ),
                }
            )

            # Ask again: either produce a final answer, or request more tools.
            text = _call_llm(out_messages)
            tool_rounds += 1

    return _invoke
