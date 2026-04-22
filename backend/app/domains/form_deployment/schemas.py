"""
Schemas for the Form Deployment domain.

Defines:
- Request models
- Response models
- Internal domain data structures

These models represent the data contracts for this domain only.
"""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID


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
    # Stable identifier for conversational context across multiple calls.
    # If omitted, the backend will generate one and return it in the response.
    session_id: Optional[UUID] = None
    last_deploy_filename: Optional[str] = None
    last_deploy_status: Optional[str] = None
    last_deploy_formId: Optional[str] = None
    last_deploy_feedback: Optional[str] = None
    last_retrieve_formId: Optional[str] = None
    last_retrieve_status: Optional[str] = None
    last_retrieve_feedback: Optional[str] = None


class FormDeploymentResponse(BaseModel):
    message: str
    session_id: UUID


class FormDeploymentDeployResponse(BaseModel):
    """Deterministic deployment attempt result.
    Reflects a real Google Forms deployment.
    """

    filename: str
    status: str
    formId: Optional[str] = None
    feedback: str

class FormDeploymentRetrieveResponse(BaseModel):
    """Deterministic retrieval attempt result."""
    
    formId: str
    status: str
    feedback: str
    content: Optional[str] = None # Not retained
