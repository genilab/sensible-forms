from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Insight:
    id: str
    dataset_id: str 
    insight_type: str   # e.g., "statistical_trend", "common_theme", "outlier_detection"
    summary: str    # Human-readable summary of the insight
    
    confidence: float   # (Possibility score between 0 and 1)

    evidence: Dict[str, Any]
    # example:
    # {
    #   "question_ids": ["Q3"],
    #   "response_count": 247,
    #   "source_files": ["responses_fall.csv", "responses_spring.csv"]
    # }

    statistics: Dict[str, Any]
    # example:
    # {
    #   "mean": 4.1,
    #   "std_dev": 0.6,
    #   "distribution": {...}
    # }
