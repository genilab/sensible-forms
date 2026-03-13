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


def ensure_last_human_message(
    messages: List[Any],
    *,
    last_user_prompt: str | None = None,
    fallback_prompt: str = "",
) -> List[Any]:
    """Ensure `messages` ends with a LangChain `HumanMessage`.

    Some providers (notably Gemini / Google GenAI) require the final prompt
    message to be from the user.

    Strategy:
    - If the last message is already a HumanMessage: return unchanged.
    - Else if any HumanMessage exists: move the most recent one to the end.
    - Else append a HumanMessage built from `last_user_prompt` or `fallback_prompt`.
    """

    from langchain_core.messages import HumanMessage

    if messages and isinstance(messages[-1], HumanMessage):
        return messages

    last_human_index: int | None = next(
        (i for i in range(len(messages) - 1, -1, -1) if isinstance(messages[i], HumanMessage)),
        None,
    )
    if last_human_index is not None:
        last_h = messages[last_human_index]
        reordered = [m for i, m in enumerate(messages) if i != last_human_index] + [last_h]
        return reordered

    if isinstance(last_user_prompt, str) and last_user_prompt.strip():
        return messages + [HumanMessage(content=last_user_prompt)]

    return messages + [HumanMessage(content=fallback_prompt)]
