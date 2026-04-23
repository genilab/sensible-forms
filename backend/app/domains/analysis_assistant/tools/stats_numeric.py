from __future__ import annotations

from typing import Any

import pandas as pd

from app.domains.analysis_assistant.tools.filters import FilterClause, apply_filters


def describe_numeric(
    df: pd.DataFrame,
    *,
    column: str,
    filters: list[FilterClause] | None = None,
) -> dict[str, Any]:
    if column not in df.columns:
        raise ValueError(f"Unknown column: {column}")

    fdf = apply_filters(df, filters)
    s = pd.to_numeric(fdf[column], errors="coerce")

    if not s.notna().any():
        return {
            "type": "describe_numeric",
            "column": column,
            "rows_used": int(fdf.shape[0]),
            "count": 0,
            "missing": int(s.isna().sum()),
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }

    return {
        "type": "describe_numeric",
        "column": column,
        "rows_used": int(fdf.shape[0]),
        "count": int(s.notna().sum()),
        "missing": int(s.isna().sum()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "min": float(s.min()),
        "max": float(s.max()),
    }
