"""
Analysis Assistant API routes.

Responsible for:
- Handling HTTP requests for survey data analysis
- Validating input data
- Calling the Analysis Assistant domain service
- Returning structured responses to the client

Contains HTTP-layer logic only.
"""

# Example Code:
from fastapi import APIRouter
from app.domains.analysis_assistant.service import AnalysisAssistantService
from app.domains.analysis_assistant.schemas import (
    AnalysisRequest,
    AnalysisResponse,
)
from app.infrastructure.llm.factory import get_llm_client

router = APIRouter(prefix="/analysis", tags=["Analysis Assistant"])


@router.post("/", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    service = AnalysisAssistantService(get_llm_client())
    return service.analyze(request)
