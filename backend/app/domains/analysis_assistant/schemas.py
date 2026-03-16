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


class AnalysisRequest(BaseModel):
    data_summary: str
    # Stable identifier for conversational context across multiple calls.
    # If omitted, the backend will generate one and return it in the response.
    session_id: Optional[UUID] = None


class AnalysisResponse(BaseModel):
    insights: str
    session_id: UUID
