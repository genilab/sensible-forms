"""Mock LLM client.

Used for local development and for repository examples where no external
LLM provider credentials are configured.

This keeps the example data-flow runnable end-to-end without requiring
API keys or third-party SDK installs.
"""

from __future__ import annotations

from typing import Any, Optional

from app.infrastructure.llm.client import LLMClient


class MockLLMClient(LLMClient):
    def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        lowered = prompt.lower()

        # Return line-based bullets for agents that parse lines.
        if "return 3-5" in lowered and "insight" in lowered:
            return "\n".join(
                [
                    "- Mock insight: response pattern looks consistent.",
                    "- Mock insight: consider segmenting by key cohorts.",
                    "- Mock insight: watch for drop-off at mid-survey.",
                ]
            )

        if "topic:" in lowered and "survey questions" in lowered:
            return "\n".join(
                [
                    "- What is the primary goal you want to achieve?",
                    "- What is the biggest obstacle you face today?",
                    "- How satisfied are you with the current process?",
                    "- What would success look like in 3 months?",
                ]
            )

        # Form deployment chat: provide deterministic-feeling guidance.
        if "last deterministic deploy attempt" in lowered and "form deployment" in lowered:
            if "status: error" in lowered:
                if "missing required columns" in lowered:
                    return (
                        "Your deploy attempt failed because the CSV header is missing required columns.\n"
                        "Fix: ensure the first row contains at least: question_text, question_type.\n"
                        "Then re-upload the CSV via the Deploy action."
                    )
                if "empty" in lowered:
                    return (
                        "Your deploy attempt failed because the uploaded CSV was empty.\n"
                        "Fix: add a header row (question_text, question_type) and at least one question row."
                    )
                return (
                    "Your deploy attempt failed deterministically.\n"
                    "Fix the CSV based on the feedback shown, then re-upload via Deploy."
                )

            if "status: success" in lowered:
                return (
                    "Your deploy attempt succeeded in this example repo (mock).\n"
                    "In production, this would create/update a Google Form from your CSV."
                )

            # No deploy attempt yet.
            return (
                "To deploy: upload a .csv file via the Deploy action.\n"
                "Required header columns: question_text, question_type.\n"
                "After upload, ask me what went wrong if you get an error."
            )

        if "deployment confirmation" in lowered or "deploy" in lowered:
            return "Mock deployment complete: your form is ready to share."

        return "Mock response generated for the provided prompt."
