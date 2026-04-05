from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

# Tool for chatbot to get more detailed metadata about a SPECIFIC CSV (columns, number of rows). 
# Can be called at any time during chat, but especially useful after uploading a CSV to confirm it was ingested correctly and see what it's called.
@tool
def describe_csv(csv_id: str, state: Annotated[dict, InjectedState]) -> dict:
    """Return basic metadata (rows/columns) for a specific CSV.

    This is a lightweight inspection tool used to verify that a particular CSV
    exists and to see its schema (columns) and size (row count).

    Expectations:
    - CSVs are stored in ``state["csv_data"]``.
    - Each CSV object has: ``id``, ``num_rows``, and ``columns``.

    Args:
        csv_id: The id of the CSV to describe.
        state: LangGraph-injected state dict containing ``csv_data``.

    Returns:
        If found:
            ``{"csv_id": <id>, "rows": <num_rows>, "columns": [..]}``
        If not found:
            ``{"csv_id": <requested>, "rows": None, "columns": None, "error": "CSV not found"}``
    """
    csvs = (state or {}).get("csv_data") or []
    csv = next((c for c in csvs if getattr(c, "id", None) == csv_id), None)
    if csv is None:
        return {"csv_id": csv_id, "rows": None, "columns": None, "error": "CSV not found"}
    return {
        "csv_id": csv.id,
        "rows": csv.num_rows,
        "columns": csv.columns or [],
    }
