"""
Form Deployment API routes.

Responsible for:
- Handling HTTP requests related to survey/form deployment
- Validating request inputs
- Calling the Form Deployment domain service
- Returning appropriate HTTP responses

No domain logic should exist here.
"""

# Example Code:
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.domains.form_deployment.service import FormDeploymentService
from app.domains.form_deployment.schemas import (
    FormDeploymentRequest,
    FormDeploymentResponse,
    FormDeploymentDeployResponse,
)
from app.infrastructure.llm.factory import get_llm_client
from app.middleware.file_validation import validate_csv_file, validate_csv_required_columns

router = APIRouter(prefix="/form-deployment", tags=["Form Deployment"])


@router.post("/chat", response_model=FormDeploymentResponse)
@router.post("/", response_model=FormDeploymentResponse, include_in_schema=False)
def deployment_chat(request: FormDeploymentRequest):
    service = FormDeploymentService(get_llm_client())
    return service.chat(request)


@router.post("/deploy", response_model=FormDeploymentDeployResponse)
async def deploy_form(file: UploadFile = File(...)):
    content = await file.read()
    try:
        validate_csv_file(file.filename, file_size_bytes=len(content))
        validate_csv_required_columns(content, required_columns=["question_text", "question_type"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    service = FormDeploymentService(get_llm_client())
    return service.attempt_deploy(filename=file.filename, file_bytes=content)
