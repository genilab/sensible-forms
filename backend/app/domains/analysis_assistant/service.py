from app.domains.analysis_assistant.schemas import (
    AnalysisRequest,
    AnalysisResponse,
)
from app.domains.analysis_assistant.graph import build_graph
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.memory.checkpointers import get_checkpointer
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from app.infrastructure.llm.langchain_messages import to_langchain_messages


class AnalysisAssistantService:
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
    def __init__(self, llm_client: LLMClient):
        self._graph = build_graph(llm=llm_client, checkpointer=get_checkpointer())

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        data_summary = (request.data_summary or "").strip()
        session_id = request.session_id or uuid4()
        thread_id = f"analysis_assistant:{session_id}"

        config = {"configurable": {"thread_id": thread_id}}

        # If this thread already has checkpointed state, only send updates.
        # Sending empty lists (e.g. csv_data: []) would overwrite checkpointed state
        # and break multi-upload flows.
        has_checkpoint = bool(self._graph.get_state(config).values)

        payload: dict = {}
        if not has_checkpoint:
            payload.update(
                {
                    "messages": [],
                    "csv_data": [],
                    "datasets": [],
                    "csv_text": None,
                    "insights": [],
                    "mode": None,
                    "last_uploaded_csv_id": None,
                    "last_user_prompt": None,
                }
            )

        # Message input modes:
        # - request.messages: treat as message deltas to append (preferred for chat UIs)
        # - data_summary: legacy single-blob summary
        # - csv_text only: upload flow (no need to generate an empty prompt)
        if request.messages:
            payload["messages"] = to_langchain_messages([m.model_dump() for m in request.messages])
        elif data_summary:
            payload["messages"] = [
                HumanMessage(
                    content=(
                        "Given the following survey data summary, return 3-5 concise insights as bullet points. "
                        "Be specific and avoid generic advice.\n\n"
                        f"SURVEY DATA SUMMARY:\n{data_summary}"
                    )
                )
            ]
            payload["last_user_prompt"] = data_summary

        if request.csv_text:
            payload["csv_text"] = request.csv_text

        result = self._graph.invoke(payload, config=config)

        messages = result.get("messages") or []
        last_ai: AIMessage | None = next(
            (m for m in reversed(messages) if isinstance(m, AIMessage)), None
        )
        if last_ai is not None and isinstance(getattr(last_ai, "content", None), str):
            insights = last_ai.content
        else:
            # Fallback: preserve stable API output even if provider returns a non-AIMessage.
            insights = str(messages[-1]) if messages else ""
        return AnalysisResponse(insights=insights, session_id=session_id)
