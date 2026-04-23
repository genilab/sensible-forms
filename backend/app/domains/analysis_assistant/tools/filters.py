from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class FilterClause:
    column: str
    op: Literal["eq"]
    value: str


def apply_filters(df: pd.DataFrame, filters: list[FilterClause] | None) -> pd.DataFrame:
    if not filters:
        return df

    filtered = df
    for clause in filters:
        if clause.column not in filtered.columns:
            raise ValueError(f"Unknown column in filter: {clause.column}")
        if clause.op != "eq":
            raise ValueError(f"Unsupported filter op: {clause.op}")

        filtered = filtered[
            filtered[clause.column].astype("string").fillna("<missing>")
            == str(clause.value)
        ]
    return filtered
