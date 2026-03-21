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

from app.domains.form_deployment.schemas import (
    FormDeploymentRequest,
    FormDeploymentResponse,
    FormDeploymentDeployResponse,
)
from app.domains.form_deployment.graph import build_graph
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.memory.checkpointers import get_checkpointer
from app.middleware.file_validation import validate_csv_file, validate_csv_required_columns
from app.domains.form_deployment.tools import form_deployment_check_csv_tool, form_deployment_deploy_form_tool
from uuid import uuid4


class FormDeploymentService:
    def __init__(self, llm_client: LLMClient):
        # Deployment attempt is deterministic, but chat is LLM-assisted.
        self._graph = build_graph(llm=llm_client, checkpointer=get_checkpointer())

    def chat(self, request: FormDeploymentRequest) -> FormDeploymentResponse:
        msg = (request.message or "").strip()
        if not msg:
            session_id = request.session_id or uuid4()
            return FormDeploymentResponse(
                message="Ask a question (e.g., 'How do I deploy a CSV?' or 'What do I fix?').",
                session_id=session_id,
            )

        session_id = request.session_id or uuid4()
        thread_id = f"form_deployment:{session_id}"

        try:
            result = self._graph.invoke(
                {
                    "message": msg,
                    "last_deploy_filename": request.last_deploy_filename,
                    "last_deploy_status": request.last_deploy_status,
                    "last_deploy_feedback": request.last_deploy_feedback,
                    "messages": [],
                },
                config={"configurable": {"thread_id": thread_id}},
            )
            message = result.get("response_message") or ""
            return FormDeploymentResponse(message=message, session_id=session_id)
        except Exception:
            # Keep the example repo resilient even if a real provider is misconfigured.
            if request.last_deploy_status:
                feedback = f" {request.last_deploy_feedback}" if request.last_deploy_feedback else ""
                return FormDeploymentResponse(
                    message=(
                        f"Deterministic deployment status: {request.last_deploy_status}."
                        + (f" Last file: {request.last_deploy_filename}." if request.last_deploy_filename else "")
                        + feedback
                    ),
                    session_id=session_id,
                )
            return FormDeploymentResponse(
                message="Upload a CSV via Deploy first, or ask for the required columns and steps.",
                session_id=session_id,
            )

    def attempt_deploy(self, *, filename: str, file_bytes: bytes) -> FormDeploymentDeployResponse:
        """Deterministically validate a CSV and return a deployment status.

        This does NOT deploy to Google Forms in this example repo.
        It only demonstrates how a dedicated form deployment endpoint could behave.
        """

        # Check CSV file structure
        try:
            validate_csv_file(filename, file_size_bytes=len(file_bytes))
        except ValueError as e:
            return FormDeploymentDeployResponse(
                filename=filename,
                status="error",
                feedback=str(e),
            )

        # Check CSV file columns
        required = ["question_id", "question_text", "question_type", "response_options", "scale_min", "scale_max", "scale_min_label", "scale_max_label", "required"]
        try:
            validate_csv_required_columns(file_bytes, required_columns=required)
        except ValueError as e:
            return FormDeploymentDeployResponse(
                filename=filename,
                status="error",
                feedback=str(e),
            )

        # Check CSV file content
        try:
            form_deployment_check_csv_tool(file_bytes)
        except ValueError as e:
            return FormDeploymentDeployResponse(
                filename=filename,
                status="error",
                feedback=str(e),
            )

        # Additional logic for deployment
        response = None
        try:
            response = form_deployment_deploy_form_tool(filename, file_bytes)
            ### In the near future, some measure to store formId data for the user should be added
        except ValueError as e:
            return FormDeploymentDeployResponse(
                filename=filename,
                status="error",
                feedback=str(e),
            )
        
        # Successfull deployment return
        return FormDeploymentDeployResponse(
            filename=filename,
            status="success",
            feedback=(
                "Example deployment succeeded!\n"
                f"Form ID: {response["formId"]}\n"
                f"Publisher link: https://docs.google.com/forms/d/{response["formId"]}/edit\n"
                f"Responder link: {response["responderUri"]}"
            ),
        )
