"""
File Upload API routes.

Responsible for:
- Handling file upload requests
- Applying file validation checks
- Passing files to storage infrastructure (e.g., GCS)
- Returning upload status and metadata

Does not contain business logic or AI behavior.
"""

# Example Code:
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.infrastructure.storage.gcs import GCSClient
from app.middleware.file_validation import validate_csv_file

router = APIRouter(prefix="/uploads", tags=["Uploads"])

storage = GCSClient()


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    try:
        validate_csv_file(file.filename, file_size_bytes=len(content))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    storage.upload_file(content, file.filename)
    return {"filename": file.filename}
