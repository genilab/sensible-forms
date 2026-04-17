"""Analysis Assistant Domain Service.

This is the domain-level entry point called by the FastAPI layer.

Responsibilities:
- Translate request models into graph input state
- Orchestrate the LangGraph workflow for the analysis assistant
- Map graph output state back into response models

Boundary note:
- HTTP concerns (status codes, request parsing) belong in `backend/app/api/*`.
- LLM prompt/tool orchestration belongs in the graph/nodes.
"""

from uuid import uuid4

from app.domains.analysis_assistant.graph import build_graph
from app.domains.analysis_assistant.schemas import AnalysisChatRequest, AnalysisChatResponse
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.memory.checkpointers import get_checkpointer


class AnalysisAssistantService:
    def __init__(self, llm_client: LLMClient):
        # Compile the graph once for this service instance.
        # The checkpointer is what enables conversation state to persist across turns.
        self._graph = build_graph(llm=llm_client, checkpointer=get_checkpointer())

    def chat(self, request: AnalysisChatRequest) -> AnalysisChatResponse:
        """Run one chat turn through the Analysis Assistant graph."""

        # `session_id` is the stable ID the client can send back on subsequent turns.
        # If absent, we create a new conversation.
        session_id = request.session_id or uuid4()
        thread_id = f"analysis_assistant:{session_id}"

        # The assistant can operate in two modes:
        # - dataset-aware: a `file_id` is present (usually from POST /analysis/uploads)
        # - dataset-agnostic: no file, just general guidance
        #
        # `filename` is a legacy field; the in-memory store currently keys by `file_id`.
        file_id = (request.file_id or request.filename or "").strip() or None

        # Normalize the message to avoid passing accidental whitespace-only prompts.
        message = (request.message or "").strip()

        # Build the initial state for the graph. Keep it minimal: nodes will add
        # derived fields like `dataset_profile`, `messages`, and `assistant_message`.
        graph_input: dict = {
            "upload_mode": bool(request.upload_mode),
            "user_message": message,
        }
        if file_id:
            # `active_file_id` tells nodes where to load the dataset from.
            graph_input["active_file_id"] = file_id

        # Run the compiled graph.
        # The `configurable.thread_id` is what binds this invocation to a checkpoint thread.
        result = self._graph.invoke(
            graph_input,
            config={"configurable": {"thread_id": thread_id}},
        )

        # Nodes generally write the assistant's output into `assistant_message`.
        # `insights` is a historical/compat alias used by some older code paths.
        assistant_message = result.get("assistant_message") or result.get("insights") or ""

        # Shape a stable API response.
        return AnalysisChatResponse(
            session_id=session_id,
            message=assistant_message,
            # Echo back the active file so the client doesn't have to track it separately.
            active_file_id=result.get("active_file_id") or file_id,
            # Present after upload-mode profiling; omitted otherwise.
            dataset_profile=result.get("dataset_profile"),
        )
