"""
Question Generation Domain Service.

Coordinates the workflow for generating survey questions.

Responsible for:
- Orchestrating agent execution
- Applying domain-level validation
- Transforming inputs and outputs
- Returning structured domain responses

Acts as the entry point for this domain's business logic.
"""

from app.domains.question_generation.schemas import (
    QuestionRequest,
    QuestionResponse,
)
from app.domains.question_generation.graph import build_graph
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.memory.checkpointers import get_checkpointer
from uuid import uuid4


class QuestionGenerationService:
    def __init__(self, llm_client: LLMClient):
        self._graph = build_graph(llm=llm_client, checkpointer=get_checkpointer())

    def generate(self, request: QuestionRequest) -> QuestionResponse:
        topic = (request.topic or "").strip()
        session_id = request.session_id or uuid4()
        thread_id = f"question_generation:{session_id}"

        result = self._graph.invoke(
            {"topic": topic, "messages": []},
            config={"configurable": {"thread_id": thread_id}},
        )
        questions = result.get("questions") or []
        return QuestionResponse(questions=questions, session_id=session_id)
