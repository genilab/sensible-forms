"""
Schemas for the Question Generation domain.

Defines:
- Request models
- Response models
- Internal domain data structures

These models represent the data contracts for this domain only.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    topic: str
    # Stable identifier for conversational context across multiple calls.
    # If omitted, the backend will generate one and return it in the response.
    session_id: Optional[UUID] = None


class QuestionResponse(BaseModel):
    questions: List[str]
    session_id: UUID
