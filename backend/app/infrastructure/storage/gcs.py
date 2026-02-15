"""
Google Cloud Storage (GCS) Client.

Responsible for:
- Uploading files
- Downloading files
- Managing storage objects
- Generating signed URLs (if needed)

Encapsulates all GCS-specific logic to keep domains infrastructure-agnostic.
"""

# Example Code:
from app.infrastructure.logging.logger import logger


class GCSClient:
    def upload_file(self, file_bytes: bytes, filename: str):
        logger.info("Mock upload of %s (%d bytes)", filename, len(file_bytes))
