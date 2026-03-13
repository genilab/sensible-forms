"""
Analysis Assistant API routes.

Responsible for:
- Handling HTTP requests for survey data analysis
- Validating input data
- Calling the Analysis Assistant domain service
- Returning structured responses to the client

Contains HTTP-layer logic only.
"""

# Example Code:
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.domains.analysis_assistant.service import AnalysisAssistantService
from app.domains.analysis_assistant.schemas import (
    AnalysisRequest,
    AnalysisResponse,
)
from app.infrastructure.llm.factory import get_llm_client
from app.middleware.file_validation import validate_csv_file

router = APIRouter(prefix="/analysis", tags=["Analysis Assistant"])


@router.post("/", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    service = AnalysisAssistantService(get_llm_client())
    return service.analyze(request)


@router.post("/upload", response_model=AnalysisResponse)
async def upload_csv_for_analysis(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
    content = await file.read()
    try:
        validate_csv_file(file.filename, file_size_bytes=len(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    decoded = content.decode("utf-8", errors="replace")

    parsed_session: UUID | None = None
    if session_id:
        try:
            parsed_session = UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id (expected UUID).")

    service = AnalysisAssistantService(get_llm_client())
    return service.analyze(
        AnalysisRequest(
            csv_text=decoded,
            session_id=parsed_session,
        )
    )
