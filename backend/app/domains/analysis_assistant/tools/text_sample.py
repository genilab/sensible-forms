from __future__ import annotations

from typing import Any

import pandas as pd

from app.domains.analysis_assistant.tools.filters import FilterClause, apply_filters
from app.domains.analysis_assistant.tools.text_redaction import redact_text


DEFAULT_SAMPLE_SIZE = 25
DEFAULT_RANDOM_STATE = 0
MAX_SAMPLE_CHARS = 500


def sample_text_responses(
    df: pd.DataFrame,
    *,
    column: str,
    n: int = DEFAULT_SAMPLE_SIZE,
    filters: list[FilterClause] | None = None,
    redact: bool = True,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> dict[str, Any]:
    if column not in df.columns:
        raise ValueError(f"Unknown column: {column}")

    fdf = apply_filters(df, filters)
    series = fdf[column].dropna().astype(str)

    if series.empty:
        return {
            "type": "sample_text",
            "column": column,
            "rows_used": int(fdf.shape[0]),
            "sample_size": 0,
            "samples": [],
        }

    take = min(int(n), int(series.shape[0]))
    sampled = series.sample(n=take, random_state=random_state)

    samples: list[str] = []
    for t in sampled.tolist():
        t2 = redact_text(t) if redact else t
        samples.append(t2[:MAX_SAMPLE_CHARS])

    return {
        "type": "sample_text",
        "column": column,
        "rows_used": int(fdf.shape[0]),
        "sample_size": int(take),
        "samples": samples,
        "redacted": bool(redact),
    }
