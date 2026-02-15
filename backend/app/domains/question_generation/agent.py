"""
Question Generation Agent.

Encapsulates AI behavior specific to generating survey questions.

Responsible for:
- Constructing prompts
- Calling/Invoking the LLM client
- Applying tools and guardrails
- Parsing and returning structured outputs

This file should not contain HTTP or infrastructure logic.
"""

# Example Code:
from app.domains.question_generation.prompts import SYSTEM_PROMPT
from app.infrastructure.llm.client import LLMClient


class QuestionGenerationAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, topic: str):
        prompt = f"{SYSTEM_PROMPT}\nTopic: {topic}"
        response = self.llm.invoke(prompt)
        return [line.strip("- ") for line in response.splitlines() if line.strip()]