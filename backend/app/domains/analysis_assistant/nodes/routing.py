from __future__ import annotations

from langgraph.graph import END
from langchain_core.messages import AIMessage

from app.domains.analysis_assistant.nodes.state import State


def route(state: State):
    """Route from START to either csv_loader (if there's new CSV text to ingest) or chatbot (if not)."""
    return "csv_loader" if state.get("csv_text") else "chatbot"


def route_after_chatbot(state: State):
    """Route after chatbot: if last message from bot included tool calls, route to tool_node, otherwise end."""
    last_message = state["messages"][-1]

    # If we are (still) in upload mode, end the graph after chatbot (don't let it call tools or loop back)
    if state.get("mode") == "upload":
        return END

    # For normal chatbot messages, if the last message from the bot included tool calls, route to tool_node, otherwise end.
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"

    return END


def route_after_ingestion(state: State):
    """Route after ingestion.

    In upload flows we prefer to end in the deterministic `upload_ack` node
    (unless ingestion requested tool execution).
    """
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and getattr(messages[-1], "tool_calls", None):
        return "tool_node"

    if state.get("mode") == "upload":
        return "upload_ack"

    return "chatbot"


def route_after_tool_node(state: State):
    """Route after ToolNode.

    In upload flows, finish with deterministic acknowledgement rather than
    invoking the full chatbot LLM call.
    """

    return "upload_ack" if state.get("mode") == "upload" else "chatbot"
