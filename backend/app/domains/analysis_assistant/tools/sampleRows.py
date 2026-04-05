from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def sample_rows(
    csv_id: str,
    state: Annotated[dict, InjectedState],
    n: int = 5,
):
    """Return a small sample of rows from a previously uploaded/loaded CSV.

    This is a lightweight inspection tool: it helps the agent/user quickly
    understand what data is present (shape, keys, example values) before choosing
    downstream actions like selecting columns, creating datasets, or running
    aggregation/insight tools.

    Expectations:
    - The CSV must already be present in the analysis assistant state under
      ``state["csv_data"]``.
    - Each CSV object is expected to have an ``id`` attribute and a ``sample(k)``
      method.

    Args:
        csv_id: The id of the CSV to sample from.
        state: LangGraph-injected state dict that contains ``csv_data``.
        n: Requested sample size. This tool clamps ``n`` to the range [0, 50].
           Passing ``None`` is treated as 0.

    Returns:
        - If the CSV exists: the return value of ``csv.sample(safe_n)``.
          (In this codebase that is typically ``list[dict]`` rows.)
        - If the CSV is not found:
          ``{"csv_id": ..., "rows": [], "error": "CSV not found"}``.
    """

    csvs = (state or {}).get("csv_data") or []
    csv = next((c for c in csvs if getattr(c, "id", None) == csv_id), None)
    if csv is None:
        return {"csv_id": csv_id, "rows": [], "error": "CSV not found"}

    safe_n = max(0, min(int(n or 0), 50))
    return csv.sample(safe_n)
