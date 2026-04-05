from typing import Optional, List, Set

from app.domains.analysis_assistant.structs.csvFile import CSVFile

PRIORITY_QID_COLS = ["question_id", "qid", "q_id", "questionId", "id"]


def find_question_id_column(columns: List[str] | None) -> Optional[str]:
    """Return the preferred question id column name if present."""
    cols = columns or []
    for k in PRIORITY_QID_COLS:
        if k in cols:
            return k
    return None


def _collect_question_ids(questions_csv: CSVFile, qid_col: str, limit: int = 200) -> Set[str]:
    qids: Set[str] = set()
    for row in questions_csv.rows[:limit]:
        val = row.get(qid_col)
        if val is not None:
            qids.add(str(val))
    return qids


def detect_wide_response_columns(
    questions_csv: CSVFile,
    responses: List[CSVFile],
    limit: int = 200,
) -> List[str]:
    """
    Detect wide-format response columns by matching question IDs against response CSV column names.
    Prefer intersection across responses; fall back to union if intersection is empty.
    Returns a sorted list of matched column names, or empty list.
    """
    qid_col = find_question_id_column(questions_csv.columns)
    if not qid_col:
        return []

    qids = _collect_question_ids(questions_csv, qid_col, limit)
    if not qids:
        return []

    all_matches: List[Set[str]] = []
    for r in responses:
        matches = {c for c in (r.columns or []) if c in qids}
        all_matches.append(matches)

    if not all_matches:
        return []

    common = set.intersection(*all_matches) if len(all_matches) > 1 else all_matches[0]
    if common:
        return sorted(common)

    union = set().union(*all_matches)
    return sorted(union)
