from __future__ import annotations

from typing import Any

import pandas as pd

from app.domains.analysis_assistant.tools.filters import FilterClause, apply_filters


def crosstab(
    df: pd.DataFrame,
    *,
    row: str,
    col: str,
    filters: list[FilterClause] | None = None,
) -> dict[str, Any]:
    if row not in df.columns:
        raise ValueError(f"Unknown row column: {row}")
    if col not in df.columns:
        raise ValueError(f"Unknown col column: {col}")

    fdf = apply_filters(df, filters)
    tab = pd.crosstab(
        fdf[row].astype("string").fillna("<missing>"),
        fdf[col].astype("string").fillna("<missing>"),
        dropna=False,
    )

    return {
        "type": "crosstab",
        "row": row,
        "col": col,
        "rows_used": int(fdf.shape[0]),
        "table": {
            str(r): {str(c): int(tab.loc[r, c]) for c in tab.columns} for r in tab.index
        },
    }
