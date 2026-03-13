from langchain.tools import tool
from langgraph.prebuilt import InjectedState
from typing import Annotated
import statistics
import math

from app.domains.analysis_assistant.tools.utils.confidence import score_numeric_aggregation
from app.domains.analysis_assistant.tools.utils.number_parse import try_parse_float

@tool
def aggregate_column(
    csv_id: str,
    column: str,
    operation: str,
    state: Annotated[dict, InjectedState],
):
    """Aggregate a numeric column (mean, median, min, max)."""
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

    values = []

    for v in csv.column_values(column):
        parsed = try_parse_float(v)
        if parsed is None:
            continue
        values.append(parsed)

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

    if not values:
        row_count = getattr(csv, "num_rows", None)
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

    row_count = getattr(csv, "num_rows", None)
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


def _weighted_mean(pairs: list[tuple[float, float]]) -> float:
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return 0.0
    return sum(x * w for x, w in pairs) / total_w


def _weighted_variance(pairs: list[tuple[float, float]], mean: float) -> float:
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return 0.0
    return sum(w * (x - mean) ** 2 for x, w in pairs) / total_w


@tool
def aggregate_column_multi(
    csv_ids: list[str],
    column: str,
    operation: str,
    state: Annotated[dict, InjectedState],
):
    """Aggregate a numeric column across multiple CSVs (mean, median, min, max).

    Returns:
    - pooled result across all values
    - per-file results/stats
    - confidence that accounts for sample size/coverage and cross-file consistency
    """

    ids = [c for c in (csv_ids or []) if c]
    if not ids:
        return {
            "csv_ids": csv_ids,
            "column": column,
            "operation": operation,
            "result": None,
            "error": "No csv_ids provided.",
        }

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

    # Strict validation: ensure the column exists in all CSVs
    missing_cols = [cid for cid in ids if column not in (csv_lookup[cid].columns or [])]
    if missing_cols:
        return {
            "csv_ids": ids,
            "column": column,
            "operation": op,
            "result": None,
            "error": f"Column '{column}' missing from CSV(s): {', '.join(missing_cols)}",
        }

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

    pooled_result = ops[op](pooled_values)
    pooled_conf = score_numeric_aggregation(
        numeric_count=total_numeric_count,
        row_count=total_row_count or None,
        operation=op,
    )

    # Cross-file consistency: compare per-file metrics for mean/median.
    metric_pairs: list[tuple[float, float]] = []
    files_with_numeric = 0
    for item in per_file:
        n = int(item.get("stats", {}).get("numeric_count") or 0)
        r = item.get("result")
        if n > 0 and isinstance(r, (int, float)):
            files_with_numeric += 1
            metric_pairs.append((float(r), float(n)))

    consistency_score = 1.0
    heterogeneity = None
    if op in {"mean", "median"} and len(metric_pairs) >= 2:
        m = _weighted_mean(metric_pairs)
        var = _weighted_variance(metric_pairs, m)
        stdev = math.sqrt(max(0.0, var))
        denom = max(1.0, abs(m))
        heterogeneity = stdev / denom
        # Map heterogeneity -> [0,1], higher is better.
        # het=0.0 -> 1.0; het=0.25 -> ~0.37; het=0.10 -> ~0.67
        consistency_score = math.exp(-heterogeneity / 0.25)

    # Blend: don't over-penalize disagreement, but reflect it.
    final_conf = pooled_conf * (0.60 + 0.40 * consistency_score)
    final_conf = min(0.95, max(0.05, final_conf))

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
