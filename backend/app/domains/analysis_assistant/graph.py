from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.core.state import BaseState
from app.domains.analysis_assistant.nodes.build_messages import build_messages
from app.domains.analysis_assistant.nodes.invoke_llm import make_invoke_llm_node
from app.infrastructure.llm.client import LLMClient


class AnalysisAssistantState(BaseState, total=False):
    data_summary: str
    insights: str


def build_graph(*, llm: LLMClient, checkpointer=None):
    graph = StateGraph(AnalysisAssistantState)

    graph.add_node("build_messages", build_messages)
    graph.add_node("invoke_llm", make_invoke_llm_node(llm))

    graph.set_entry_point("build_messages")
    graph.add_edge("build_messages", "invoke_llm")
    graph.add_edge("invoke_llm", END)

    return graph.compile(checkpointer=checkpointer)
