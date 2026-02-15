"""
Analysis Assistant Agent.

Encapsulates AI logic for analyzing survey results and providing insights.

Responsible for:
- Constructing prompts
- Calling/Invoking the LLM client
- Applying tools and guardrails
- Parsing and returning structured outputs

This file should not contain HTTP or infrastructure logic.
"""

# Example Code:
from app.domains.analysis_assistant.prompts import SYSTEM_PROMPT
from app.infrastructure.llm.client import LLMClient


class AnalysisAssistantAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, data_summary: str):
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "Survey summary:\n"
            f"{data_summary}\n\n"
            "Return 3-5 concise insights as bullet points."
        )
        # Some providers (e.g., Gemini) will truncate when max tokens is small.
        # Keep this comfortably above typical 3-5 bullet responses.
        return self.llm.invoke(prompt, max_tokens=1024)