from __future__ import annotations

from langgraph.graph import StateGraph

from app.infrastructure.llm.client import LLMClient


# Default state shape for the Analysis Assistant now matches the routed
# pipeline (chat + optional CSV ingestion + tools).
from app.domains.analysis_assistant.nodes.state import State as AnalysisAssistantState


def build_graph(*, llm: LLMClient, checkpointer=None):
    """Build the Analysis Assistant graph.

    (CSV ingestion + tool-using chatbot).
    """

    # Local imports keep module import side-effects low.
    from langgraph.graph import END as _END
    from langgraph.graph import START
    from langgraph.prebuilt import ToolNode

    from app.domains.analysis_assistant.nodes.chatbot import make_chatbot_node
    from app.domains.analysis_assistant.nodes.csv_loader import csv_loader
    from app.domains.analysis_assistant.nodes.ingestion_orchestrator import (
        make_ingestion_orchestrator_node,
    )
    from app.domains.analysis_assistant.nodes.routing import (
        route_entry,
        route_after_chatbot,
    )
    from app.domains.analysis_assistant.nodes.tools import tools
    from app.domains.analysis_assistant.nodes.upload_ack import upload_ack

    builder = StateGraph(AnalysisAssistantState)

    builder.add_node("csv_loader", csv_loader)
    builder.add_node("ingestion_orchestrator", make_ingestion_orchestrator_node(llm))
    builder.add_node("tool_node", ToolNode(tools))
    builder.add_node("chatbot", make_chatbot_node(llm))
    builder.add_node("upload_ack", upload_ack)

    # Route_entry: Begin by either ingesting a freshly uploaded CSV blob, or just chatting.
    builder.add_conditional_edges(
        START,
        route_entry,
        {
            "csv_loader": "csv_loader",
            "chatbot": "chatbot",
        },
    )

    # CSV ingestion pipeline: loader -> orchestrator -> upload acknowledgement
    builder.add_edge("csv_loader", "ingestion_orchestrator")
    builder.add_edge("ingestion_orchestrator", "upload_ack")
    builder.add_edge("upload_ack", _END)    # Upload acknowledgement is always terminal.


    # Chat pipeline: chatbot -> (tools?) -> chatbot -> (tools?.../end)
    builder.add_conditional_edges(
        "chatbot",
        route_after_chatbot,
        {
            "tool_node": "tool_node",
            _END: _END,
        },
    )
    builder.add_edge("tool_node", "chatbot")

    return builder.compile(checkpointer=checkpointer)