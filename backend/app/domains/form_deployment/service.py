"""
Form Deployment Domain Service.

Coordinates form deployment workflows and agent interactions.

Responsible for:
- Orchestrating agent execution
- Applying *domain-level* validation
- Transforming inputs and outputs
- Returning structured domain responses

Acts as the entry point for this domain's business logic.
"""

from __future__ import annotations

# Example Code:
from app.domains.form_deployment.agent import FormDeploymentAgent
from app.domains.form_deployment.schemas import (
    FormDeploymentRequest,
    FormDeploymentResponse,
    FormDeploymentDeployResponse,
)
from app.infrastructure.llm.client import LLMClient
from app.middleware.file_validation import validate_csv_file, validate_csv_required_columns


class FormDeploymentService:
    def __init__(self, llm_client: LLMClient):
        # Deployment attempt is deterministic, but chat is LLM-assisted.
        self.agent = FormDeploymentAgent(llm_client)

    def chat(self, request: FormDeploymentRequest):
        result = self.agent.run(
            request.message,
            last_deploy_filename=request.last_deploy_filename,
            last_deploy_status=request.last_deploy_status,
            last_deploy_feedback=request.last_deploy_feedback,
        )
        return FormDeploymentResponse(message=result)

    def attempt_deploy(self, *, filename: str, file_bytes: bytes) -> FormDeploymentDeployResponse:
        """Deterministically validate a CSV and return a deployment status.

        This does NOT deploy to Google Forms in this example repo.
        It only demonstrates how a dedicated form deployment endpoint could behave.
        """

        try:
            validate_csv_file(filename, file_size_bytes=len(file_bytes))
        except ValueError as e:
            return FormDeploymentDeployResponse(
                filename=filename,
                status="error",
                feedback=str(e),
            )

        required = ["question_text", "question_type"]
        try:
            validate_csv_required_columns(file_bytes, required_columns=required)
        except ValueError as e:
            return FormDeploymentDeployResponse(
                filename=filename,
                status="error",
                feedback=str(e),
            )

        # Additional logic for deployment would go here in a production implementation.

        return FormDeploymentDeployResponse(
            filename=filename,
            status="success",
            feedback=(
                "Example deployment succeeded (mock). "
                "In production this would create/update a Google Form from your CSV."
            ),
        )
