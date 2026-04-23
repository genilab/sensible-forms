from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.domains.analysis_assistant.tools.types import ColumnKind


# Profiling heuristics (tunable)
_DATETIME_DETECTION_SAMPLE_SIZE = 25
_DATETIME_DETECTION_MIN_OK = 5
_DATETIME_DETECTION_MIN_OK_PCT = 0.7

_CATEGORICAL_MAX_UNIQUE = 20
_TOP_VALUES_MAX_K = 10

_MIN_ROW_DENOMINATOR = 1


@dataclass(frozen=True)
class DatasetProfile:
    row_count: int
    column_count: int
    columns: list[str]
    column_kinds: dict[str, ColumnKind]
    missing: dict[str, dict[str, float]]
    top_values: dict[str, list[dict[str, Any]]]
    numeric_summary: dict[str, dict[str, float]]
    timestamp_column: str | None

    def to_compact_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.columns,
            "column_kinds": self.column_kinds,
            "missing": self.missing,
            "top_values": self.top_values,
            "numeric_summary": self.numeric_summary,
            "timestamp_column": self.timestamp_column,
        }

    def to_compact_json(self) -> str:
        return json.dumps(self.to_compact_dict(), ensure_ascii=False)


def _is_datetime_series(s: pd.Series) -> bool:
    if s.empty:
        return False
    if pd.api.types.is_datetime64_any_dtype(s):
        return True

    sample = s.dropna().astype(str).head(_DATETIME_DETECTION_SAMPLE_SIZE)
    if sample.empty:
        return False

    parsed = pd.to_datetime(sample, errors="coerce", utc=True)
    ok = int(parsed.notna().sum())
    return ok >= max(
        _DATETIME_DETECTION_MIN_OK,
        math.ceil(len(sample) * _DATETIME_DETECTION_MIN_OK_PCT),
    )


def infer_column_kinds(df: pd.DataFrame) -> dict[str, ColumnKind]:
    kinds: dict[str, ColumnKind] = {}

    for col in df.columns:
        series = df[col]

        if pd.api.types.is_bool_dtype(series):
            kinds[col] = "categorical"
            continue

        if pd.api.types.is_numeric_dtype(series):
            kinds[col] = "numeric"
            continue

        if _is_datetime_series(series):
            kinds[col] = "datetime"
            continue

        non_null = series.dropna().astype(str)
        if non_null.empty:
            kinds[col] = "unknown"
            continue

        unique = non_null.nunique(dropna=True)
        if unique <= _CATEGORICAL_MAX_UNIQUE:
            kinds[col] = "categorical"
        else:
            kinds[col] = "text"

    return kinds


def build_profile(df: pd.DataFrame) -> DatasetProfile:
    kinds = infer_column_kinds(df)

    missing: dict[str, dict[str, float]] = {}
    for col in df.columns:
        miss_count = int(df[col].isna().sum())
        missing[col] = {
            "count": float(miss_count),
            "pct": float(miss_count / max(_MIN_ROW_DENOMINATOR, df.shape[0])),
        }

    top_values: dict[str, list[dict[str, Any]]] = {}
    for col, kind in kinds.items():
        if kind != "categorical":
            continue

        vc = (
            df[col]
            .astype("string")
            .fillna("<missing>")
            .value_counts(dropna=False)
            .head(_TOP_VALUES_MAX_K)
        )
        top_values[col] = [
            {"value": str(idx), "count": int(count)} for idx, count in vc.items()
        ]

    numeric_summary: dict[str, dict[str, float]] = {}
    for col, kind in kinds.items():
        if kind != "numeric":
            continue

        s = pd.to_numeric(df[col], errors="coerce")
        numeric_summary[col] = {
            "count": float(int(s.notna().sum())),
            "missing": float(int(s.isna().sum())),
            "mean": float(s.mean()) if s.notna().any() else float("nan"),
            "median": float(s.median()) if s.notna().any() else float("nan"),
            "min": float(s.min()) if s.notna().any() else float("nan"),
            "max": float(s.max()) if s.notna().any() else float("nan"),
        }

    timestamp_column: str | None = None
    for col, kind in kinds.items():
        if kind == "datetime":
            timestamp_column = col
            break
    if timestamp_column is None:
        for col in df.columns:
            if "time" in col.lower() and "submit" in col.lower():
                timestamp_column = col
                break

    return DatasetProfile(
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
        columns=list(df.columns),
        column_kinds=kinds,
        missing=missing,
        top_values=top_values,
        numeric_summary=numeric_summary,
        timestamp_column=timestamp_column,
    )
