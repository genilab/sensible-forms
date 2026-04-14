"""
Schemas for the Analysis Assistant domain.

Defines:
- Request models
- Response models
- Internal domain data structures

These models represent the data contracts for this domain only.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AnalysisChatRequest(BaseModel):
    # Stable identifier for conversational context across multiple calls.
    session_id: Optional[UUID] = None

    # The user's chat message.
    message: str

    # When true, the backend will profile the uploaded CSV and proactively suggest analyses.
    upload_mode: bool = False

    # Identifier returned by POST /analysis/uploads/ (preferred) or POST /uploads/ (legacy).
    file_id: Optional[str] = None

    # Legacy support (if a client only has a filename).
    filename: Optional[str] = None


class AnalysisChatResponse(BaseModel):
    session_id: UUID
    message: str

    # Convenience echo for the client.
    active_file_id: Optional[str] = None

    # Compact dataset profile (no raw rows). Present after upload_mode profiling.
    dataset_profile: Optional[dict] = None
