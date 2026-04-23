"""Analysis Assistant API routes.

This module is the HTTP boundary for the Analysis Assistant domain.

Responsibilities:
- Accept HTTP requests (FastAPI)
- Validate/parse payloads via Pydantic models
- Delegate to the domain service (business logic)
- Return structured responses to the client

Design note:
- Keep HTTP-layer code thin; the domain service owns orchestration and LLM behavior.
"""

from fastapi import APIRouter

from app.domains.analysis_assistant.schemas import AnalysisChatRequest, AnalysisChatResponse
from app.domains.analysis_assistant.service import AnalysisAssistantService
from app.infrastructure.llm.factory import get_llm_client

# All Analysis Assistant routes hang off the "/analysis" prefix.
router = APIRouter(prefix="/analysis", tags=["Analysis Assistant"])


@router.post("/chat", response_model=AnalysisChatResponse)
def chat(request: AnalysisChatRequest) -> AnalysisChatResponse:
    """Chat endpoint for the Analysis Assistant.

    Flow (high level):
    1) Parse the JSON body into `AnalysisChatRequest`.
    2) Create the domain service with an LLM client selected by configuration.
    3) Delegate to `AnalysisAssistantService.chat()`, which runs the LangGraph workflow.
    4) Return an `AnalysisChatResponse`.

    Notes:
    - Creating the service per-request is fine here because it mainly holds a compiled
      graph and a reference to the LLM client.
    """

    # `get_llm_client()` returns a provider-agnostic LLM implementation (OpenAI/Gemini/Mock).
    service = AnalysisAssistantService(get_llm_client())

    # The service returns a Pydantic model, which FastAPI serializes to JSON.
    return service.chat(request)
