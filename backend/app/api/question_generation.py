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
    # Setting a maximum number of prompt attempts
    MAX_ATTEMPTS = 3
    service = QuestionGenerationService(get_llm_client())
    response = service.generate(request)

    # Prompting the LLM again if the response is an empty list
    if (response.questions == []):
        i = 0
        while (i < MAX_ATTEMPTS):
            i += 1
            try:
                # If the response is not empty, return the response
                assert response.questions != []
                return response
            except:
                # Otherwise, submit the prompt again
                response = service.generate(request)
        # If a valid response is not returned within MAX_ATTEMPTS,
        #   request the user try again or reload
        response.questions = ["I was not able to complete your request.\n"
            "Please try again or save any important information and reload the page."]
        return response
    
    # If a valid response was received initially, return the response
    return response
