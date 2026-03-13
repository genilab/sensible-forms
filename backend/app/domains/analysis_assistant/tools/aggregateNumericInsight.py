from __future__ import annotations

import math
import statistics
import uuid
from typing import Annotated, Any, Dict, List, Optional, Tuple

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.domains.analysis_assistant.structs.insights import Insight
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.utils.confidence import score_numeric_aggregation
from app.domains.analysis_assistant.tools.utils.number_parse import try_parse_float
from app.domains.analysis_assistant.tools.utils.question_resolve import resolve_question_id
from app.domains.analysis_assistant.tools.utils.survey_helpers import (
    extract_long_response_value,
    known_question_ids,
    resolve_question_text,
)


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


def _to_float(value: Any) -> Optional[float]:
    return try_parse_float(value)


@tool
def aggregate_numeric_question_insight(
    dataset_id: str,
    question_id: str,
    operation: str,
    state: Annotated[dict, InjectedState] = None,
    runtime: Any = None,
) -> Command:
    """Aggregate numeric responses for a specific question in a SurveyDataset and store as an Insight.

    Works for both:
    - wide responses: question_id corresponds to a column
    - long responses: question_id found in join_key_responses and numeric value in response/answer/value

    Returns updated insights list.
    """

    state = state or {}
    if runtime is None:  # pragma: no cover
        raise ValueError("ToolRuntime was not injected.")

    datasets = state.get("datasets", [])
    dataset = next((d for d in datasets if d.id == dataset_id), None)
    if dataset is None:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"No dataset found for dataset_id={dataset_id!r}.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    resolved_qid = resolve_question_id(user_ref=str(question_id), known_ids=known_question_ids(dataset))

    ops = {
        "mean": statistics.mean,
        "median": statistics.median,
        "min": min,
        "max": max,
    }
    op = (operation or "").strip().lower()
    if op not in ops:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Unsupported operation {operation!r}. Supported: {sorted(ops.keys())}.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    pooled_values: list[float] = []
    per_file: list[dict] = []
    total_candidate_rows = 0
    total_numeric_count = 0

    for resp_csv in dataset.responses:
        file_values: list[float] = []
        candidate_rows = 0

        if dataset.responses_wide:
            # Each row is a respondent; question_id is a column
            if resolved_qid not in (resp_csv.columns or []):
                # Skip this file; do not hard-fail.
                per_file.append(
                    {
                        "csv_id": resp_csv.id,
                        "result": None,
                        "confidence": 0.05,
                        "stats": {
                            "numeric_count": 0,
                            "row_count": getattr(resp_csv, "num_rows", None),
                            "missing_column": True,
                        },
                    }
                )
                continue

            for row in resp_csv.rows:
                candidate_rows += 1
                v = _to_float(row.get(resolved_qid))
                if v is None:
                    continue
                file_values.append(v)
        else:
            # Long/tidy: filter rows matching question_id
            qcol = dataset.join_key_responses or ""
            if not qcol or qcol not in (resp_csv.columns or []):
                per_file.append(
                    {
                        "csv_id": resp_csv.id,
                        "result": None,
                        "confidence": 0.05,
                        "stats": {
                            "numeric_count": 0,
                            "row_count": getattr(resp_csv, "num_rows", None),
                            "missing_join_key": True,
                        },
                    }
                )
                continue

            for row in resp_csv.rows:
                if str(row.get(qcol)) != str(resolved_qid):
                    continue
                candidate_rows += 1
                _, raw = extract_long_response_value(row)
                v = _to_float(raw)
                if v is None:
                    continue
                file_values.append(v)

        pooled_values.extend(file_values)
        pooled_n = len(file_values)
        total_numeric_count += pooled_n
        total_candidate_rows += candidate_rows

        file_stats: Dict[str, Any] = {
            "numeric_count": pooled_n,
            "row_count": candidate_rows,
        }
        if pooled_n:
            try:
                file_stats["min"] = min(file_values)
                file_stats["max"] = max(file_values)
                file_stats["mean"] = statistics.mean(file_values)
                if pooled_n >= 2:
                    file_stats["stdev"] = statistics.stdev(file_values)
            except Exception:
                pass

        per_file.append(
            {
                "csv_id": resp_csv.id,
                "result": ops[op](file_values) if file_values else None,
                "confidence": score_numeric_aggregation(
                    numeric_count=pooled_n,
                    row_count=candidate_rows or None,
                    operation=op,
                ),
                "stats": file_stats,
            }
        )

    if not pooled_values:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=(
                            f"No numeric values found for dataset_id={dataset_id!r}, question_id={question_id!r}."
                        ),
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    pooled_result = ops[op](pooled_values)
    pooled_conf = score_numeric_aggregation(
        numeric_count=total_numeric_count,
        row_count=total_candidate_rows or None,
        operation=op,
    )

    # Cross-file consistency (only meaningful for mean/median)
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
        consistency_score = math.exp(-heterogeneity / 0.25)

    final_conf = pooled_conf * (0.60 + 0.40 * consistency_score)
    final_conf = min(0.95, max(0.05, final_conf))

    question_text = resolve_question_text(dataset, resolved_qid)
    question_label = question_text or f"Question {resolved_qid}"

    stats: Dict[str, Any] = {
        "numeric_count": total_numeric_count,
        "row_count": total_candidate_rows or None,
        "file_count": len(dataset.responses),
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

    summary = f"{question_label}: {op} = {pooled_result} (n={total_numeric_count})"

    insight = Insight(
        id=str(uuid.uuid4()),
        dataset_id=dataset.id,
        insight_type="numeric_aggregation",
        summary=summary,
        confidence=float(final_conf),
        evidence={
            "question_id": resolved_qid,
            "question_text": question_text,
            "operation": op,
            "responses_wide": dataset.responses_wide,
            "source_csv_ids": [c.id for c in dataset.responses],
        },
        statistics=stats,
    )

    return Command(
        update={
            "insights": [insight],
            "messages": [
                ToolMessage(
                    content=summary,
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
