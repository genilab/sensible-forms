"""
Form Deployment API routes.

Responsible for:
- Handling HTTP requests related to survey/form deployment
- Validating request inputs
- Calling the Form Deployment domain service
- Returning appropriate HTTP responses

No domain logic should exist here.
"""

from fastapi import Request, APIRouter, UploadFile, File
from app.domains.form_deployment.service import FormDeploymentService
from app.domains.form_deployment.schemas import (
    FormDeploymentRequest,
    FormDeploymentResponse,
    FormDeploymentDeployResponse,
    FormDeploymentRetrieveResponse,
)
from app.infrastructure.llm.factory import get_llm_client


router = APIRouter(prefix="/form-deployment", tags=["Form Deployment"])


@router.post("/chat", response_model=FormDeploymentResponse)
@router.post("/", response_model=FormDeploymentResponse, include_in_schema=False)
def deployment_chat(request: FormDeploymentRequest):
    service = FormDeploymentService(get_llm_client())
    return service.chat(request)


@router.post("/deploy", response_model=FormDeploymentDeployResponse)
async def deploy_form(file: UploadFile = File(...), request: Request = None): # pyright: ignore[reportArgumentType]
    # Get refresh token
    refresh_token = None
    if request:
        refresh_token = request.cookies.get("refresh_token")
    
    # Read content and assert instance properties
    content = await file.read()
    assert isinstance(file.filename, str)
    
    # Get and return deployment data
    service = FormDeploymentService(get_llm_client())
    return service.attempt_deploy(filename=file.filename, file_bytes=content, refresh_token=refresh_token)


@router.get("/retrieve", response_model=FormDeploymentRetrieveResponse)
async def retrieve_form(formId: str, request: Request):
    # Get refresh token
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return FormDeploymentRetrieveResponse(
            formId=formId,
            status="error",
            feedback='Please press "Login to Google Forms".'
        )

    # Get and return retrieval data
    service = FormDeploymentService(get_llm_client())
    return service.attempt_retrieve(formId=formId, refresh_token=refresh_token)
