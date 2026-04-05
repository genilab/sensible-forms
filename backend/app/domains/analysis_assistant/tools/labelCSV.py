from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

from app.domains.analysis_assistant.structs.csvFile import CSVFile

# FALLBACK: infer_label_for_csv and label_csv are not currently used in the graph, but are available as tools for the chatbot to call if it wants to assign labels to CSVs (e.g. inferred from content or based on user instructions).
def infer_label_for_csv(csv_file: CSVFile) -> str | None:
    """Infer a best-effort label for a CSV using deterministic heuristics.

    This helper attempts to recognize common survey shapes and returns a simple
    label such as ``"questions"`` or ``"responses"``.

    Notes:
    - This is intentionally conservative; it returns ``None`` if it cannot infer.
    - It does not inspect cell values, only column names.

    Args:
        csv_file: The CSV to classify.

    Returns:
        A string label (e.g. ``"questions"`` / ``"responses"``) or ``None``.
    """
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
    """Assign/update a human-readable label for a CSV already in state.

    This tool mutates the in-memory CSV object found in ``state["csv_data"]`` by
    setting its ``label`` field. The label is used elsewhere to refer to CSVs in
    a more user-friendly way (e.g. distinguishing multiple response CSVs).

    Args:
        csv_id: The id of the CSV to label.
        label: The label to assign.
        state: LangGraph-injected state dict containing ``csv_data``.

    Returns:
        A short status string describing what happened.
    """
    for csv in (state or {}).get("csv_data") or []:
        if csv.id == csv_id:
            csv.label = label
            return f"CSV {csv_id} labeled as '{label}'"
    return "CSV not found"
