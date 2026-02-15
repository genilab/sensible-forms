"""
Form Deployment Agent.

Encapsulates AI-assisted logic for deploying and managing forms.

Responsible for:
- Constructing prompts
- Calling/Invoking the LLM client
- Applying tools and guardrails
- Parsing and returning structured outputs

This file should not contain HTTP or infrastructure logic.
"""

# Example Code:
from __future__ import annotations

from typing import Optional

from app.domains.form_deployment.prompts import SYSTEM_PROMPT
from app.infrastructure.llm.client import LLMClient


class FormDeploymentAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(
        self,
        message: str,
        *,
        last_deploy_filename: Optional[str] = None,
        last_deploy_status: Optional[str] = None,
        last_deploy_feedback: Optional[str] = None,
    ) -> str:
        msg = (message or "").strip()
        if not msg:
            return "Ask a question (e.g., 'How do I deploy a CSV?' or 'What do I fix?')."

        context = (
            "Last deterministic deploy attempt:\n"
            f"- filename: {last_deploy_filename or 'null'}\n"
            f"- status: {last_deploy_status or 'null'}\n"
            f"- feedback: {last_deploy_feedback or 'null'}\n"
        )

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"{context}\n"
            f"User question: {msg}\n\n"
            "Answer:"
        )

        try:
            return self.llm.invoke(prompt, temperature=0.2)
        except Exception:
            # Keep the example repo resilient even if a real provider is misconfigured.
            if last_deploy_status:
                feedback = f" {last_deploy_feedback}" if last_deploy_feedback else ""
                return (
                    f"Deterministic deployment status: {last_deploy_status}."
                    + (f" Last file: {last_deploy_filename}." if last_deploy_filename else "")
                    + feedback
                )
            return "Upload a CSV via Deploy first, or ask for the required columns and steps."
