"""Utilities for working with LangChain messages.

We normalize the various message shapes used across this repo into LangChain
`BaseMessage` instances.

Accepted inputs:
- str
- list[dict] with {role, content}
- list[LangChain BaseMessage]
- mixed lists (best-effort)
"""

from __future__ import annotations

from typing import Any, List


def to_langchain_messages(messages: Any) -> List[Any]:
    """Convert `messages` into a LangChain-compatible message list."""

    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    if isinstance(messages, str):
        return [HumanMessage(content=messages)]

    if isinstance(messages, list):
        converted: list[Any] = []
        for item in messages:
            if isinstance(item, dict):
                role = (item.get("role") or "user").lower()
                content = str(item.get("content") or "")
                if role == "system":
                    converted.append(SystemMessage(content=content))
                elif role in {"assistant", "ai"}:
                    converted.append(AIMessage(content=content))
                else:
                    converted.append(HumanMessage(content=content))
            else:
                # Assume it's already a BaseMessage (or similar). Keep as-is.
                converted.append(item)
        return converted

    return [HumanMessage(content=str(messages))]
