"""
Schemas for the Question Generation domain.

Defines:
- Request models
- Response models
- Internal domain data structures

These models represent the data contracts for this domain only.
"""

# Example Code:
from pydantic import BaseModel
from typing import List


class QuestionRequest(BaseModel):
    topic: str


class QuestionResponse(BaseModel):
    questions: List[str]
