"""
Question Generation API routes.

Responsible for:
- Handling HTTP requests related to survey question generation
- Validating incoming request payloads
- Calling the Question Generation domain service
- Returning structured HTTP responses

This layer should only manage I/O concerns.
Business logic belongs in the domain layer.
"""

# Example Code:
from fastapi import APIRouter
from app.domains.question_generation.service import QuestionGenerationService
from app.domains.question_generation.schemas import (
    QuestionRequest,
    QuestionResponse,
)
from app.infrastructure.llm.factory import get_llm_client

router = APIRouter(prefix="/question-generation", tags=["Question Generation"])


@router.post("/", response_model=QuestionResponse)
def generate_questions(request: QuestionRequest):
    service = QuestionGenerationService(get_llm_client())
    return service.generate(request)
