from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

# Useful tool for chatbot to list available CSVs and their basic metadata (number of rows/columns). 
# Can be called at any time during chat, but especially useful after uploading a CSV to confirm it was ingested correctly and see what it's called.
@tool
def list_csvs(state: Annotated[dict, InjectedState]) -> str:
    """List available CSVs currently loaded into assistant state.

    This is a convenience/inspection tool that lets the agent or user confirm what
    CSVs are present after upload/ingestion.

    Expectations:
    - CSVs are stored in ``state["csv_data"]``.
    - Each CSV object has: ``id``, ``num_rows``, and ``columns``.

    Args:
        state: LangGraph-injected state dict that contains ``csv_data``.

    Returns:
        A newline-delimited string of the form:
        ``<csv_id>: <num_rows> rows, <num_columns> columns``.

        Returns an empty string if no CSVs exist.
    """
    csvs = state.get("csv_data", [])
    return "\n".join(
        f"{c.id}: {c.num_rows} rows, {len(c.columns or [])} columns"
        for c in csvs
    )
