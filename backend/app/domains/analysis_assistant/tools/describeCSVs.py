from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def describe_csv(csv_id: str, state: Annotated[dict, InjectedState]) -> dict:
    """Get metadata for a CSV file."""
    csvs = (state or {}).get("csv_data") or []
    csv = next((c for c in csvs if getattr(c, "id", None) == csv_id), None)
    if csv is None:
        return {"csv_id": csv_id, "rows": None, "columns": None, "error": "CSV not found"}
    return {
        "csv_id": csv.id,
        "rows": csv.num_rows,
        "columns": csv.columns or [],
    }
