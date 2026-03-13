from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def list_csvs(state: Annotated[dict, InjectedState]) -> str:
    """List all available CSV files."""
    csvs = state.get("csv_data", [])
    return "\n".join(
        f"{c.id}: {c.num_rows} rows, {len(c.columns or [])} columns"
        for c in csvs
    )
