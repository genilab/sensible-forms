"""
File Upload API routes.

Responsible for:
- Handling file upload requests
- Applying file validation checks
- Storing uploaded bytes for later domain processing
- Returning upload status and metadata

Does not contain business logic or AI behavior.
"""

# Example Code:
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.middleware.file_validation import validate_csv_file
from app.domains.analysis_assistant.file_store import save_file

router = APIRouter(prefix="/uploads", tags=["Uploads"])
analysis_router = APIRouter(prefix="/analysis/uploads", tags=["Analysis Assistant"])


async def _upload_csv(file: UploadFile) -> dict:
    content = await file.read()
    try:
        validate_csv_file(file.filename, file_size_bytes=len(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_id = save_file(content, filename=file.filename)
    return {"filename": file.filename, "file_id": file_id}


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    return await _upload_csv(file)


@analysis_router.post("/")
async def upload_analysis_assistant_csv(file: UploadFile = File(...)):
    return await _upload_csv(file)
