"""File Upload API routes.

These endpoints are the HTTP boundary for file uploads.

Responsibilities:
- Accept multipart file uploads (FastAPI's `UploadFile`)
- Apply lightweight validation (type/size)
- Store uploaded bytes in a short-lived, process-local store (for later analysis)
- Return a `file_id` that the frontend can pass to the Analysis Assistant chat endpoint

Important:
- This module does *not* do any LLM work or domain orchestration.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.domains.analysis_assistant.file_store import save_file
from app.middleware.file_validation import validate_csv_file

router = APIRouter(prefix="/uploads", tags=["Uploads"])

# Canonical Analysis Assistant upload path.
analysis_router = APIRouter(prefix="/analysis/uploads", tags=["Analysis Assistant"])


async def _upload_csv(file: UploadFile) -> dict:
    """Implementation used by the upload routes.

    Returns a JSON object with:
    - filename: original client filename
    - file_id: opaque ID for retrieving the stored bytes later
    """

    # Read the entire file into memory. (The domain store is in-memory as well.)
    content = await file.read()

    # Validate at the HTTP boundary so downstream domain logic can assume inputs are sane.
    try:
        validate_csv_file(file.filename, file_size_bytes=len(content))
    except ValueError as e:
        # Convert domain/validation errors into an HTTP 400 response.
        raise HTTPException(status_code=400, detail=str(e))

    # Store bytes for later retrieval by the Analysis Assistant graph nodes.
    file_id = save_file(content, filename=file.filename)
    return {"filename": file.filename, "file_id": file_id}


@analysis_router.post("/", operation_id="upload_analysis_assistant_csv")
@router.post("/", operation_id="upload_file", deprecated=True)
async def upload_csv(file: UploadFile = File(...)):
    """Upload a CSV file.

    Endpoints:
    - POST /analysis/uploads/ (canonical for Analysis Assistant)
    - POST /uploads/ (legacy alias; deprecated)

    Returns: {filename, file_id}
    """

    return await _upload_csv(file)
