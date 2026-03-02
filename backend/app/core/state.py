"""Shared LangGraph/LangChain state types.

This module provides a single canonical place to define the `messages` field used
when building LangGraph graphs.

Why this exists:
- Avoid redefining `messages: Annotated[list, add_messages]` in multiple files
- Keep a consistent state shape across graphs/agents

Note:
- This repo's current agents still primarily pass prompt strings.
- You can adopt LangGraph incrementally by importing `BaseState`/`MessagesState`.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

try:
    # LangGraph reducer that appends new messages into the running message list.
    from langgraph.graph.message import add_messages
except Exception:  # pragma: no cover
    add_messages = None  # type: ignore[assignment]


# A permissive message list type; works with:
# - LangChain BaseMessage objects
# - dicts like {role, content}
# - plain strings
Messages = list[Any]


class MessagesState(TypedDict):
    """Minimal state containing only messages."""

    # `add_messages` is used by LangGraph to merge message history.
    # If LangGraph isn't installed, this remains a type-level hint only.
    messages: Annotated[Messages, add_messages]  # type: ignore[arg-type]


# Alias to make intent clearer at call sites.
BaseState = MessagesState
