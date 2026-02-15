"""
Schemas for the Analysis Assistant domain.

Defines:
- Request models
- Response models
- Internal domain data structures

These models represent the data contracts for this domain only.
"""

# Example Code:
from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    data_summary: str


class AnalysisResponse(BaseModel):
    insights: str
