from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset


DEFAULT_QUESTION_TEXT_KEYS = ["question", "question_text", "text", "prompt", "label"]


def resolve_question_text(dataset: SurveyDataset, question_id: str) -> Optional[str]:
    """Resolve a readable question text from the questions CSV for a given id."""

    key = dataset.join_key_questions
    for row in dataset.questions.rows:
        if str(row.get(key)) == str(question_id):
            for k in DEFAULT_QUESTION_TEXT_KEYS:
                if k in row and str(row.get(k) or "").strip():
                    return str(row.get(k)).strip()
    return None


def known_question_ids(dataset: SurveyDataset) -> set[str]:
    """Return the set of known question IDs for conservative user-ref resolution."""

    key = dataset.join_key_questions
    known: set[str] = set()
    if key:
        for row in dataset.questions.rows:
            v = row.get(key)
            if v is not None:
                known.add(str(v))

    # Also include response column names for wide datasets.
    if dataset.responses_wide and dataset.responses:
        known.update(str(c) for c in (dataset.responses[0].columns or []) if c is not None)

    return known


def extract_long_response_value(row: Dict[str, Any]) -> Tuple[Optional[str], Any]:
    """Extract the response value field in long/tidy response rows."""

    for k in ("response", "answer", "value"):
        if k in row and row.get(k) not in (None, ""):
            return k, row.get(k)
    return None, None
