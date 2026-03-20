from __future__ import annotations

from typing import Any, Callable, Dict

from app.infrastructure.llm.client import LLMClient


def make_invoke_llm_node(llm: LLMClient) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def _invoke(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages") or []
        text = llm.invoke_llm(messages)
        return {
            "messages": [{"role": "assistant", "content": text}],
            "raw_response": text,
        }

    return _invoke
