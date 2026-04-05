from __future__ import annotations

import math
import statistics
from typing import Annotated

from langchain.tools import tool
from langgraph.prebuilt import InjectedState

from app.domains.analysis_assistant.tools.utils.confidence import (
    MAXIMUM_CONFIDENCE_SCORE,
    MINIMUM_CONFIDENCE_SCORE,
    score_numeric_aggregation,
)
from app.domains.analysis_assistant.tools.utils.number_parse import try_parse_float
from app.domains.analysis_assistant.tools.utils.weighted_stats import weighted_mean, weighted_variance


# Numeric stability / confidence tuning constants.
_VARIANCE_FLOOR = 0.0
_DENOMINATOR_FLOOR = 1.0
_CONSISTENCY_SCORE_DEFAULT = 1.0

# How strongly to down-weight pooled confidence when per-file results disagree.
_CONSISTENCY_BLEND_BASE = 0.60
_CONSISTENCY_BLEND_WEIGHT = 0.40

# Scale for converting heterogeneity into a (0,1] consistency score.
# Smaller => harsher penalty for disagreement.
_HETEROGENEITY_DECAY_SCALE = 0.25


@tool
def aggregate_column_multi(
    csv_ids: list[str],
    column: str,
    operation: str,
    state: Annotated[dict, InjectedState],
):
    """Aggregate a numeric column across multiple CSVs (mean/median/min/max).

    This tool:
    - validates that all referenced CSV ids exist in ``state["csv_data"]``
    - validates that the requested column exists in all CSVs
    - parses numeric values using ``try_parse_float`` (skipping non-numeric)
    - computes a pooled result across all parsed values
    - produces per-file results/stats and a confidence score

    Confidence combines:
    - base confidence from ``score_numeric_aggregation`` (coverage/sample size)
    - an optional cross-file consistency penalty for mean/median when per-file
      metrics disagree

    Args:
        csv_ids: List of CSV ids to aggregate.
        column: Column name that must exist in all CSVs.
        operation: One of ``mean``, ``median``, ``min``, ``max``.
        state: LangGraph-injected state dict containing ``csv_data``.

    Returns:
        A dict containing pooled ``result``, ``confidence``, and a ``stats`` payload.
        On failure, returns a dict with ``error`` populated and ``result`` set to ``None``.
    """

    # ---- 1) Normalize inputs and validate CSV ids exist ----
    ids = [c for c in (csv_ids or []) if c]
    if not ids:
        return {
            "csv_ids": csv_ids,
            "column": column,
            "operation": operation,
            "result": None,
            "error": "No csv_ids provided.",
        }

    # Index all known CSVs for fast lookup.
    csv_data = state.get("csv_data") or []
    csv_lookup = {c.id: c for c in csv_data}
    missing = [cid for cid in ids if cid not in csv_lookup]
    if missing:
        return {
            "csv_ids": ids,
            "column": column,
            "operation": operation,
            "result": None,
            "error": f"CSV(s) not found: {', '.join(missing)}",
        }

    # ---- 2) Validate requested aggregation operation ----
    ops = {
        "mean": statistics.mean,
        "median": statistics.median,
        "min": min,
        "max": max,
    }
    op = (operation or "").strip().lower()
    if op not in ops:
        return {
            "csv_ids": ids,
            "column": column,
            "operation": operation,
            "result": None,
            "error": f"Unsupported operation '{operation}'. Choose one of: {', '.join(sorted(ops.keys()))}.",
        }

    # ---- 3) Strict column validation across all CSVs (multi-file aggregation assumes same schema) ----
    missing_cols = [cid for cid in ids if column not in (csv_lookup[cid].columns or [])]
    if missing_cols:
        return {
            "csv_ids": ids,
            "column": column,
            "operation": op,
            "result": None,
            "error": f"Column '{column}' missing from CSV(s): {', '.join(missing_cols)}",
        }

    # ---- 4) Collect numeric values per file and build per-file stats ----
    pooled_values: list[float] = []
    per_file: list[dict] = []
    total_row_count = 0
    total_numeric_count = 0

    for cid in ids:
        csv = csv_lookup[cid]
        row_count = getattr(csv, "num_rows", None)
        if isinstance(row_count, int) and row_count > 0:
            total_row_count += row_count

        values: list[float] = []
        for v in csv.column_values(column):
            parsed = try_parse_float(v)
            if parsed is None:
                continue
            values.append(parsed)

        numeric_count = len(values)
        total_numeric_count += numeric_count
        pooled_values.extend(values)

        file_stats = {
            "numeric_count": numeric_count,
            "row_count": row_count,
        }
        if values:
            try:
                file_stats["min"] = min(values)
                file_stats["max"] = max(values)
                file_stats["mean"] = statistics.mean(values)
                if numeric_count >= 2:
                    file_stats["stdev"] = statistics.stdev(values)
            except Exception:
                pass

        per_file.append(
            {
                "csv_id": cid,
                "result": ops[op](values) if values else None,
                "confidence": score_numeric_aggregation(
                    numeric_count=numeric_count,
                    row_count=row_count,
                    operation=op,
                ),
                "stats": file_stats,
            }
        )

    # ---- 5) If nothing usable was found across all files, return error + diagnostics ----
    if not pooled_values:
        return {
            "csv_ids": ids,
            "column": column,
            "operation": op,
            "result": None,
            "error": "No numeric values found for the requested column across the provided CSVs.",
            "confidence": score_numeric_aggregation(
                numeric_count=0,
                row_count=total_row_count or None,
                operation=op,
            ),
            "stats": {
                "numeric_count": 0,
                "row_count": total_row_count or None,
                "file_count": len(ids),
                "files_with_numeric": 0,
                "per_file": per_file,
            },
        }

    # ---- 6) Compute pooled aggregation + base confidence from coverage/sample size ----
    pooled_result = ops[op](pooled_values)
    pooled_conf = score_numeric_aggregation(
        numeric_count=total_numeric_count,
        row_count=total_row_count or None,
        operation=op,
    )

    # ---- 7) Cross-file consistency adjustment ----
    metric_pairs: list[tuple[float, float]] = []
    files_with_numeric = 0
    for item in per_file:
        n = int(item.get("stats", {}).get("numeric_count") or 0)
        r = item.get("result")
        if n > 0 and isinstance(r, (int, float)):
            files_with_numeric += 1
            metric_pairs.append((float(r), float(n)))

    consistency_score = _CONSISTENCY_SCORE_DEFAULT
    heterogeneity = None
    if op in {"mean", "median"} and len(metric_pairs) >= 2:
        m = weighted_mean(metric_pairs)
        var = weighted_variance(metric_pairs, m)
        stdev = math.sqrt(max(_VARIANCE_FLOOR, var))
        denom = max(_DENOMINATOR_FLOOR, abs(m))
        heterogeneity = stdev / denom
        consistency_score = math.exp(-heterogeneity / _HETEROGENEITY_DECAY_SCALE)

    # ---- 8) Blend base confidence with consistency score; clamp to avoid extremes ----
    final_conf = pooled_conf * (_CONSISTENCY_BLEND_BASE + _CONSISTENCY_BLEND_WEIGHT * consistency_score)
    final_conf = min(MAXIMUM_CONFIDENCE_SCORE, max(MINIMUM_CONFIDENCE_SCORE, final_conf))

    # ---- 9) Build statistics payload and return results ----
    stats = {
        "numeric_count": total_numeric_count,
        "row_count": total_row_count or None,
        "file_count": len(ids),
        "files_with_numeric": files_with_numeric,
        "per_file": per_file,
    }
    try:
        stats["min"] = min(pooled_values)
        stats["max"] = max(pooled_values)
        stats["mean"] = statistics.mean(pooled_values)
        if total_numeric_count >= 2:
            stats["stdev"] = statistics.stdev(pooled_values)
    except Exception:
        pass
    if heterogeneity is not None:
        stats["consistency"] = {
            "metric": "weighted_stdev_over_mean",
            "value": heterogeneity,
            "score": consistency_score,
        }

    return {
        "csv_ids": ids,
        "column": column,
        "operation": op,
        "result": pooled_result,
        "confidence": final_conf,
        "stats": stats,
    }
