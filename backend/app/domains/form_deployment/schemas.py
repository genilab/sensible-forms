"""
Schemas for the Form Deployment domain.

Defines:
- Request models
- Response models
- Internal domain data structures

These models represent the data contracts for this domain only.
"""

# Example Code: Form deployment is upload-to-deploy (deterministic) plus chat for follow-up instructions.
from pydantic import BaseModel
from typing import Optional


class FormDeploymentRequest(BaseModel):
    """Chat-style request for the form deployment assistant.

    The deployment itself is deterministic and happens via `POST /form-deployment/deploy`.
    This request is for follow-up questions like:
        - "Did it deploy?"
        - "What should I fix?"
        - "What do I do next?"

    The UI can include the most recent deploy attempt status/feedback so chat responses
    are grounded in what happened.
    """

    message: str
    last_deploy_filename: Optional[str] = None
    last_deploy_status: Optional[str] = None
    last_deploy_feedback: Optional[str] = None


class FormDeploymentResponse(BaseModel):
    message: str


class FormDeploymentDeployResponse(BaseModel):
    """Deterministic deployment attempt result.

    In production this would reflect a real Google Forms deployment.
    In this example repo, it demonstrates validation + status reporting.
    """

    filename: str
    status: str
    feedback: str