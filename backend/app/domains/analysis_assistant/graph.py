from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.core.state import BaseState
from app.domains.analysis_assistant.nodes.build_messages import build_messages
from app.infrastructure.llm.client import LLMClient
from app.domains.analysis_assistant.nodes.invoke_llm_with_tools import (
    make_invoke_llm_with_tools_node,
)
from app.domains.analysis_assistant.nodes.profile_csv import profile_csv


class AnalysisAssistantState(BaseState, total=False):
    data_summary: str
    insights: str

    # Chat + upload pipeline (minimal)
    upload_mode: bool
    user_message: str
    active_file_id: str
    dataset_profile: dict
    assistant_message: str


def route_mode(state: dict[str, Any]) -> dict[str, Any]:
    # Router node doesn't modify state; conditional edges decide the next node.
    return {}


def build_graph(*, llm: LLMClient, checkpointer=None):
    graph = StateGraph(AnalysisAssistantState)

    graph.add_node("route_mode", route_mode)
    graph.add_node("profile_csv", profile_csv)
    graph.add_node("build_messages", build_messages)
    graph.add_node("invoke_llm", make_invoke_llm_with_tools_node(llm))

    graph.set_entry_point("route_mode")
    graph.add_conditional_edges(
        "route_mode",
        lambda state: "profile_csv" if bool(state.get("upload_mode")) else "build_messages",
        {"profile_csv": "profile_csv", "build_messages": "build_messages"},
    )
    # Both paths converge to the same LLM invocation node, which may optionally run tools and then produce insights.
    graph.add_edge("profile_csv", "build_messages")
    graph.add_edge("build_messages", "invoke_llm")
    graph.add_edge("invoke_llm", END)

    return graph.compile(checkpointer=checkpointer)
