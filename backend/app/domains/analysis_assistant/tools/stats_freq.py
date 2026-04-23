from __future__ import annotations

from typing import Any

import pandas as pd

from app.domains.analysis_assistant.tools.filters import FilterClause, apply_filters


DEFAULT_TOP_K = 20


def freq(
    df: pd.DataFrame,
    *,
    column: str,
    filters: list[FilterClause] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    if column not in df.columns:
        raise ValueError(f"Unknown column: {column}")

    fdf = apply_filters(df, filters)
    vc = (
        fdf[column]
        .astype("string")
        .fillna("<missing>")
        .value_counts(dropna=False)
        .head(top_k)
    )
    return {
        "type": "freq",
        "column": column,
        "top_k": top_k,
        "rows_used": int(fdf.shape[0]),
        "values": [{"value": str(k), "count": int(v)} for k, v in vc.items()],
    }
