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
    AnalysisChatRequest,
    AnalysisChatResponse,
)
from app.domains.analysis_assistant.graph import build_graph
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.memory.checkpointers import get_checkpointer
from uuid import uuid4


class AnalysisAssistantService:
    def __init__(self, llm_client: LLMClient):
        self._graph = build_graph(llm=llm_client, checkpointer=get_checkpointer())

    def chat(self, request: AnalysisChatRequest) -> AnalysisChatResponse:
        session_id = request.session_id or uuid4()
        thread_id = f"analysis_assistant:{session_id}"

        file_id = (request.file_id or request.filename or "").strip() or None
        message = (request.message or "").strip()

        graph_input: dict = {
            "upload_mode": bool(request.upload_mode),
            "user_message": message,
        }
        if file_id:
            graph_input["active_file_id"] = file_id

        result = self._graph.invoke(
            graph_input,
            config={"configurable": {"thread_id": thread_id}},
        )

        assistant_message = (
            result.get("assistant_message")
            or result.get("insights")
            or ""
        )

        return AnalysisChatResponse(
            session_id=session_id,
            message=assistant_message,
            active_file_id=result.get("active_file_id") or file_id,
            dataset_profile=result.get("dataset_profile"),
        )
