"""Domain-owned data structures for Analysis Assistant.

These are intentionally lightweight (dataclasses) and used by tools/graph nodes.
"""

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.insights import Insight
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset

__all__ = ["CSVFile", "Insight", "SurveyDataset"]
