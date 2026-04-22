from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.core.state import BaseState
from app.domains.form_deployment.nodes.build_messages import build_messages
from app.domains.form_deployment.nodes.invoke_llm import make_invoke_llm_node
from app.infrastructure.llm.client import LLMClient


class FormDeploymentState(BaseState, total=False):
    message: str
    last_deploy_filename: str | None
    last_deploy_status: str | None
    last_deploy_formId: str | None
    last_deploy_feedback: str | None
    last_retrieve_formId: str | None
    last_retrieve_status: str | None
    last_retrieve_feedback: str | None
    response_message: str


def build_graph(*, llm: LLMClient, checkpointer=None):
    graph = StateGraph(FormDeploymentState)

    graph.add_node("build_messages", build_messages) # pyright: ignore[reportArgumentType]
    graph.add_node("invoke_llm", make_invoke_llm_node(llm)) # pyright: ignore[reportArgumentType]

    graph.set_entry_point("build_messages")
    graph.add_edge("build_messages", "invoke_llm")
    graph.add_edge("invoke_llm", END)

    return graph.compile(checkpointer=checkpointer)
