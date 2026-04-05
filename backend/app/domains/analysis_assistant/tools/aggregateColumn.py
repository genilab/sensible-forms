from __future__ import annotations

import statistics
from typing import Annotated

from langchain.tools import tool
from langgraph.prebuilt import InjectedState

from app.domains.analysis_assistant.tools.utils.confidence import score_numeric_aggregation
from app.domains.analysis_assistant.tools.utils.number_parse import try_parse_float


@tool
def aggregate_column(
    csv_id: str,
    column: str,
    operation: str,
    state: Annotated[dict, InjectedState],
):
    """Aggregate a numeric column within a single CSV (mean/median/min/max).

    This tool parses the target column into floats using ``try_parse_float``.
    Any value that cannot be parsed to a float is skipped.

    Args:
        csv_id: The id of the CSV in ``state["csv_data"]``.
        column: The column name to aggregate.
        operation: One of ``mean``, ``median``, ``min``, ``max``.
        state: LangGraph-injected state dict containing ``csv_data``.

    Returns:
        A dict containing ``result`` and diagnostic fields. On failure, returns a
        dict with ``error`` populated and ``result`` set to ``None``.
    """

    # ---- 1) Locate the requested CSV in state and validate inputs ----
    csv_data = state.get("csv_data") or []
    csv = next((c for c in csv_data if c.id == csv_id), None)
    if csv is None:
        return {
            "csv_id": csv_id,
            "column": column,
            "operation": operation,
            "result": None,
            "error": f"CSV '{csv_id}' not found.",
        }

    if column not in (csv.columns or []):
        return {
            "csv_id": csv_id,
            "column": column,
            "operation": operation,
            "result": None,
            "error": f"Column '{column}' not found in CSV '{csv_id}'.",
        }

    values: list[float] = []

    # ---- 2) Parse all numeric values from the target column ----
    # Non-numeric values are skipped; this keeps aggregation deterministic and robust.
    for v in csv.column_values(column):
        parsed = try_parse_float(v)
        if parsed is None:
            continue
        values.append(parsed)

    # ---- 3) Validate requested aggregation operation ----
    ops = {
        "mean": statistics.mean,
        "median": statistics.median,
        "min": min,
        "max": max,
    }

    op = (operation or "").strip().lower()
    if op not in ops:
        return {
            "csv_id": csv_id,
            "column": column,
            "operation": operation,
            "result": None,
            "error": f"Unsupported operation '{operation}'. Choose one of: {', '.join(sorted(ops.keys()))}.",
        }

    # ---- 4) If no numeric values were found, return an error payload + confidence/stats ----
    row_count = getattr(csv, "num_rows", None)
    if not values:
        return {
            "csv_id": csv_id,
            "column": column,
            "operation": op,
            "result": None,
            "error": "No numeric values found for the requested column.",
            "confidence": score_numeric_aggregation(
                numeric_count=0,
                row_count=row_count,
                operation=op,
            ),
            "stats": {
                "numeric_count": 0,
                "row_count": row_count,
            },
        }

    # ---- 5) Compute aggregation result + supporting stats ----
    numeric_count = len(values)

    stats = {
        "numeric_count": numeric_count,
        "row_count": row_count,
    }

    # Provide additional stats to support downstream insighting.
    # (Safe, deterministic; does not change the main "result" contract.)
    try:
        stats["min"] = min(values)
        stats["max"] = max(values)
        stats["mean"] = statistics.mean(values)
        if numeric_count >= 2:
            stats["stdev"] = statistics.stdev(values)
    except Exception:
        pass

    # ---- 6) Return result payload (keeps a stable contract for downstream tools) ----
    return {
        "csv_id": csv_id,
        "column": column,
        "operation": op,
        "result": ops[op](values),
        "confidence": score_numeric_aggregation(
            numeric_count=numeric_count,
            row_count=row_count,
            operation=op,
        ),
        "stats": stats,
    }
