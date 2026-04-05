from __future__ import annotations

from langgraph.graph import END
from langchain_core.messages import AIMessage

from app.domains.analysis_assistant.nodes.state import State


def route_entry(state: State):
    """Route from START to either csv_loader (if there's new CSV text to ingest) or chatbot (if not)."""
    return "csv_loader" if state.get("csv_text") else "chatbot"


def route_after_chatbot(state: State):
    """Route after chatbot: if last message from bot included tool calls, route to tool_node, otherwise end."""
    last_message = state["messages"][-1]

    # For normal chatbot messages, if the last message from the bot included tool calls, route to tool_node, otherwise end.
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"

    return END
