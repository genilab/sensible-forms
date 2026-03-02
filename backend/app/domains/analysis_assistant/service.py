"""
Analysis Assistant Domain Service.

Coordinates analysis assistant workflows and agent interactions.

Responsible for:
- Orchestrating agent execution
- Applying domain-level validation
- Transforming inputs and outputs
- Returning structured domain responses

Acts as the entry point for this domain's business logic.
"""

from app.domains.analysis_assistant.schemas import (
    AnalysisRequest,
    AnalysisResponse,
)
from app.domains.analysis_assistant.graph import build_graph
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.memory.checkpointers import get_checkpointer
from uuid import uuid4


class AnalysisAssistantService:
    def __init__(self, llm_client: LLMClient):
        self._graph = build_graph(llm=llm_client, checkpointer=get_checkpointer())

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        data_summary = (request.data_summary or "").strip()
        session_id = request.session_id or uuid4()
        thread_id = f"analysis_assistant:{session_id}"

        result = self._graph.invoke(
            {"data_summary": data_summary, "messages": []},
            config={"configurable": {"thread_id": thread_id}},
        )
        insights = result.get("insights") or ""
        return AnalysisResponse(insights=insights, session_id=session_id)
