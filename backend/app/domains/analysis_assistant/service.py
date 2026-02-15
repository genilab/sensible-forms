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

# Example Code:
from app.domains.analysis_assistant.agent import AnalysisAssistantAgent
from app.domains.analysis_assistant.schemas import (
    AnalysisRequest,
    AnalysisResponse,
)
from app.infrastructure.llm.client import LLMClient


class AnalysisAssistantService:
    def __init__(self, llm_client: LLMClient):
        self.agent = AnalysisAssistantAgent(llm_client)

    def analyze(self, request: AnalysisRequest):
        insights = self.agent.run(request.data_summary)
        return AnalysisResponse(insights=insights)
