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


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class AnalysisRequest(BaseModel):
    # Backward compatible input for the existing UI: a single summary blob.
    data_summary: Optional[str] = None

    # New: chat-style messages (e.g. [{role: "user", content: "..."}, ...]).
    # If provided, this is used as the model input instead of `data_summary`.
    messages: Optional[list[ChatMessage]] = None

    # Optional: raw CSV content for the ingestion branch.
    csv_text: Optional[str] = None
    # Stable identifier for conversational context across multiple calls.
    # If omitted, the backend will generate one and return it in the response.
    session_id: Optional[UUID] = None


class AnalysisResponse(BaseModel):
    insights: str
    session_id: UUID
