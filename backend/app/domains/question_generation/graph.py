from __future__ import annotations

from typing import List, TypedDict

from langgraph.graph import END, StateGraph

from app.core.state import BaseState
from app.domains.question_generation.nodes.build_messages import build_messages
from app.domains.question_generation.nodes.invoke_llm import make_invoke_llm_node
from app.domains.question_generation.nodes.parse_questions import parse_questions
from app.infrastructure.llm.client import LLMClient


class QuestionGenerationState(BaseState, total=False):
    topic: str
    raw_response: str
    questions: List[str]


def build_graph(*, llm: LLMClient, checkpointer=None):
    graph = StateGraph(QuestionGenerationState)

    graph.add_node("build_messages", build_messages)
    graph.add_node("invoke_llm", make_invoke_llm_node(llm))
    graph.add_node("parse_questions", parse_questions)

    graph.set_entry_point("build_messages")
    graph.add_edge("build_messages", "invoke_llm")
    graph.add_edge("invoke_llm", "parse_questions")
    graph.add_edge("parse_questions", END)

    return graph.compile(checkpointer=checkpointer)
