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

# Example Code:
from app.domains.question_generation.agent import QuestionGenerationAgent
from app.domains.question_generation.schemas import (
    QuestionRequest,
    QuestionResponse,
)
from app.infrastructure.llm.client import LLMClient


class QuestionGenerationService:
    def __init__(self, llm_client: LLMClient):
        self.agent = QuestionGenerationAgent(llm_client)

    def generate(self, request: QuestionRequest) -> QuestionResponse:
        questions = self.agent.run(request.topic)
        return QuestionResponse(questions=questions)
