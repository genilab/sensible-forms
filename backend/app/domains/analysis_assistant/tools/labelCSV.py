from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

from app.domains.analysis_assistant.structs.csvFile import CSVFile


def infer_label_for_csv(csv_file: CSVFile) -> str | None:
    """Best-effort deterministic labeling for common survey CSV shapes."""
    cols = set((csv_file.columns or []))

    questionish_cols = {
        "question_id",
        "question_text",
        "question_type",
        "response_options",
        "scale_min",
        "scale_max",
        "scale_min_label",
        "scale_max_label",
        "required",
    }

    if ("question_text" in cols and "question_type" in cols) or len(cols & questionish_cols) >= 3:
        return "questions"

    if "respondent_id" in cols or "response_id" in cols or "participant_id" in cols:
        return "responses"

    # Weak heuristic: lots of Q* columns implies wide responses
    q_like = [
        c
        for c in cols
        if isinstance(c, str) and len(c) >= 2 and c[0] in {"Q", "q"} and c[1:].isdigit()
    ]
    if len(q_like) >= 3:
        return "responses"

    return None

@tool
def label_csv(csv_id: str, label: str, state: Annotated[dict, InjectedState]) -> str:
    """Assign a human-readable label to a CSV file."""
    for csv in (state or {}).get("csv_data") or []:
        if csv.id == csv_id:
            csv.label = label
            return f"CSV {csv_id} labeled as '{label}'"
    return "CSV not found"
