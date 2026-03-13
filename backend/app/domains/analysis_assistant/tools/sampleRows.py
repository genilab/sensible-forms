from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def sample_rows(
    csv_id: str,
    state: Annotated[dict, InjectedState],
    n: int = 5,
):
    """Return sample rows from a CSV."""
    csvs = (state or {}).get("csv_data") or []
    csv = next((c for c in csvs if getattr(c, "id", None) == csv_id), None)
    if csv is None:
        return {"csv_id": csv_id, "rows": [], "error": "CSV not found"}
    safe_n = max(0, min(int(n or 0), 50))
    return csv.sample(safe_n)
