from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.core.state import BaseState
from app.domains.analysis_assistant.nodes.build_messages import build_messages
from app.domains.analysis_assistant.nodes.invoke_llm_with_tools import make_invoke_llm_with_tools_node
from app.domains.analysis_assistant.nodes.profile_csv import profile_csv
from app.infrastructure.llm.client import LLMClient


class AnalysisAssistantState(BaseState, total=False):
    """LangGraph state for the Analysis Assistant.

    This extends the shared `BaseState`, which defines the `messages` field and
    its reducer semantics (append messages across nodes).

    `total=False` means keys are optional; nodes add fields as they go.

    Common fields you will see:
    - `upload_mode`: if True, the graph first profiles the uploaded CSV
    - `active_file_id`: identifier for the uploaded dataset in the domain file store
    - `dataset_profile`: compact summary used to ground the prompt without sending raw rows
    - `messages`: chat-style message list passed to the LLM
    - `assistant_message`: the final assistant response for this turn
    """

    # Legacy/freeform path (still supported by prompts.py)
    data_summary: str

    # Final assistant content (also mirrored to `assistant_message` in newer nodes)
    insights: str

    # Chat + upload pipeline
    upload_mode: bool
    user_message: str
    active_file_id: str
    dataset_profile: dict
    assistant_message: str


def route_mode(state: dict[str, Any]) -> dict[str, Any]:
    """Router node.

    This node intentionally does not mutate state.

    Its only job is to let conditional edges decide the next node based on
    current state (e.g., whether this is an upload-triggered run).
    """

    return {}


def build_graph(*, llm: LLMClient, checkpointer=None):
    """Build and compile the Analysis Assistant LangGraph workflow."""

    # LangGraph builds a directed graph of nodes (functions) that transform state.
    graph = StateGraph(AnalysisAssistantState)

    # Nodes: each takes a state dict and returns a partial state update.
    graph.add_node("route_mode", route_mode)
    graph.add_node("profile_csv", profile_csv)
    graph.add_node("build_messages", build_messages)
    graph.add_node("invoke_llm", make_invoke_llm_with_tools_node(llm))

    # Entry point: always start by deciding which mode we're in.
    graph.set_entry_point("route_mode")

    # Conditional branch:
    # - If upload_mode=True, profile the CSV first (requires active_file_id)
    # - Otherwise, proceed directly to message construction
    graph.add_conditional_edges(
        "route_mode",
        lambda state: "profile_csv" if bool(state.get("upload_mode")) else "build_messages",
        {"profile_csv": "profile_csv", "build_messages": "build_messages"},
    )

    # Convergence: after profiling (if any), we always build prompt messages, then
    # invoke the model (with optional deterministic tools), then end.
    graph.add_edge("profile_csv", "build_messages")
    graph.add_edge("build_messages", "invoke_llm")
    graph.add_edge("invoke_llm", END)

    # Compilation attaches checkpointing so repeated invocations can restore message history.
    return graph.compile(checkpointer=checkpointer)
