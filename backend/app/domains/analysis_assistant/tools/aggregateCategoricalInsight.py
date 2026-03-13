from __future__ import annotations

import math
import uuid
from collections import Counter, defaultdict
from typing import Annotated, Any, Dict, List, Optional, Tuple

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.domains.analysis_assistant.structs.insights import Insight
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.utils.confidence import score_categorical_distribution
from app.domains.analysis_assistant.tools.utils.question_resolve import resolve_question_id
from app.domains.analysis_assistant.tools.utils.survey_helpers import (
    extract_long_response_value,
    known_question_ids,
    resolve_question_text,
)


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_emptyish(value: Any) -> bool:
    s = _norm(value)
    if not s:
        return True
    return s in {
        "n/a",
        "na",
        "none",
        "null",
        "no response",
        "no answer",
        "prefer not to say",
        "prefer not",
        "unknown",
        "not sure",
    }


@tool
def aggregate_categorical_question_insight(
    dataset_id: str,
    question_id: str,
    top_k: int = 5,
    state: Annotated[dict, InjectedState] = None,
    runtime: Any = None,
) -> Command:
    """Aggregate text/categorical responses for a question into a single Insight.

    Produces:
    - counts + proportions for the top responses
    - evidence: sample (csv_id, row_index, column/field, value)
    - confidence: data-driven from sample size, coverage, dominance, and cross-file consistency

    Works for both wide and long response formats.
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

    k = max(1, min(int(top_k or 5), 10))

    pooled_counter: Counter[str] = Counter()
    pooled_display: dict[str, str] = {}

    # Evidence buckets: normalized_value -> list[evidence]
    evidence_samples: dict[str, list[dict]] = defaultdict(list)

    total_candidates = 0
    total_non_empty = 0

    per_file: list[dict] = []

    for resp_csv in dataset.responses:
        file_counter: Counter[str] = Counter()
        file_display: dict[str, str] = {}
        candidates = 0
        non_empty = 0
        missing_column = False
        missing_join_key = False

        if dataset.responses_wide:
            if resolved_qid not in (resp_csv.columns or []):
                missing_column = True
            else:
                for idx, row in enumerate(resp_csv.rows):
                    candidates += 1
                    raw = row.get(resolved_qid)
                    if _is_emptyish(raw):
                        continue
                    non_empty += 1
                    n = _norm(raw)
                    file_counter[n] += 1
                    # preserve a representative display string
                    if n not in file_display:
                        file_display[n] = str(raw).strip()
                    if len(evidence_samples[n]) < 3:
                        evidence_samples[n].append(
                            {
                                "csv_id": resp_csv.id,
                                "row_index": idx,
                                "column": resolved_qid,
                                "value": str(raw).strip(),
                            }
                        )
        else:
            qcol = dataset.join_key_responses or ""
            if not qcol or qcol not in (resp_csv.columns or []):
                missing_join_key = True
            else:
                for idx, row in enumerate(resp_csv.rows):
                    if str(row.get(qcol)) != str(resolved_qid):
                        continue
                    candidates += 1
                    field, raw = extract_long_response_value(row)
                    if _is_emptyish(raw):
                        continue
                    non_empty += 1
                    n = _norm(raw)
                    file_counter[n] += 1
                    if n not in file_display:
                        file_display[n] = str(raw).strip()
                    if len(evidence_samples[n]) < 3:
                        evidence_samples[n].append(
                            {
                                "csv_id": resp_csv.id,
                                "row_index": idx,
                                "field": field,
                                "value": str(raw).strip(),
                            }
                        )

        total_candidates += candidates
        total_non_empty += non_empty

        # merge into pooled
        pooled_counter.update(file_counter)
        for n, disp in file_display.items():
            pooled_display.setdefault(n, disp)

        # per-file stats
        file_total = sum(file_counter.values())
        top_items = file_counter.most_common(1)
        top_norm = top_items[0][0] if top_items else None
        top_count = top_items[0][1] if top_items else 0
        top_share = (top_count / file_total) if file_total else 0.0

        second_share = 0.0
        if file_total and len(file_counter) >= 2:
            second_count = file_counter.most_common(2)[1][1]
            second_share = second_count / file_total

        margin = max(0.0, top_share - second_share)
        conf = score_categorical_distribution(
            non_empty_count=file_total,
            candidate_count=candidates or None,
            top_share=top_share,
            margin=margin,
            consistency_score=None,
        )

        per_file.append(
            {
                "csv_id": resp_csv.id,
                "top_value": pooled_display.get(top_norm) if top_norm else None,
                "confidence": conf,
                "stats": {
                    "non_empty_count": file_total,
                    "candidate_count": candidates,
                    "unique_count": len(file_counter),
                    "missing_column": missing_column,
                    "missing_join_key": missing_join_key,
                },
            }
        )

    if total_non_empty == 0 or not pooled_counter:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=(
                            f"No non-empty categorical values found for dataset_id={dataset_id!r}, question_id={question_id!r}."
                        ),
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    pooled_total = sum(pooled_counter.values())
    top = pooled_counter.most_common(k)

    # compute pooled dominance stats
    top_norm, top_count = top[0]
    top_share = top_count / pooled_total if pooled_total else 0.0

    unique_count = len(pooled_counter)

    second_share = 0.0
    if pooled_total and len(pooled_counter) >= 2:
        second_count = pooled_counter.most_common(2)[1][1]
        second_share = second_count / pooled_total
    margin = max(0.0, top_share - second_share)

    # consistency across files: do files agree on the global top value?
    files_with_data = 0
    files_matching_top = 0
    top_shares: list[float] = []
    for item in per_file:
        ne = int(item.get("stats", {}).get("non_empty_count") or 0)
        if ne <= 0:
            continue
        files_with_data += 1
        if _norm(item.get("top_value")) == _norm(pooled_display.get(top_norm)):
            files_matching_top += 1

        # approximate top share for stability from per-file counters is not stored;
        # derive a proxy from unique_count (weak), so skip and just use agreement.

    agreement = (files_matching_top / files_with_data) if files_with_data else 1.0
    consistency_score = agreement

    confidence = score_categorical_distribution(
        non_empty_count=pooled_total,
        candidate_count=total_candidates or None,
        top_share=top_share,
        margin=margin,
        consistency_score=consistency_score if files_with_data >= 2 else None,
    )

    question_text = resolve_question_text(dataset, resolved_qid)
    question_label = question_text or f"Question {resolved_qid}"

    top_values: list[dict] = []
    for n, c in top:
        disp = pooled_display.get(n, n)
        top_values.append(
            {
                "value": disp,
                "count": c,
                "share": c / pooled_total if pooled_total else 0.0,
                "evidence": evidence_samples.get(n, [])[:3],
            }
        )

    # Open-ended / high-diversity handling:
    # If every non-empty response is unique, there is no meaningful "most common".
    diversity_ratio = (unique_count / pooled_total) if pooled_total else 0.0
    all_unique = pooled_total > 0 and unique_count == pooled_total

    # "Mostly unique" means near-singletons, so even a "top" value isn't really consensus.
    mostly_unique = pooled_total >= 8 and diversity_ratio >= 0.9 and top_count <= 2

    # "Minor mode" means there is a most common response worth reporting,
    # but the distribution is still very diverse overall.
    minor_mode = (
        pooled_total >= 8
        and diversity_ratio >= 0.75
        and top_count >= 2
        and top_share <= 0.35
    )

    if all_unique:
        summary = f"{question_label}: all responses are unique (n={pooled_total})."
    elif mostly_unique:
        summary = (
            f"{question_label}: responses are highly diverse with no clear consensus "
            f"(unique={unique_count}, n={pooled_total}; top frequency={top_count}, {top_share:.0%})."
        )
    elif minor_mode:
        summary = (
            f"{question_label}: most common response is '{pooled_display.get(top_norm, top_norm)}' "
            f"({top_share:.0%}, n={pooled_total}), but responses are still highly diverse "
            f"(unique={unique_count}, {diversity_ratio:.0%} unique)."
        )
    else:
        summary = (
            f"{question_label}: most common response is '{pooled_display.get(top_norm, top_norm)}' "
            f"({top_share:.0%}, n={pooled_total})"
        )

    insight = Insight(
        id=str(uuid.uuid4()),
        dataset_id=dataset.id,
        insight_type="categorical_distribution",
        summary=summary,
        confidence=float(confidence),
        evidence={
            "question_id": resolved_qid,
            "question_text": question_text,
            "responses_wide": dataset.responses_wide,
            "source_csv_ids": [c.id for c in dataset.responses],
            "top_values": top_values,
            "diversity": {
                "unique_count": unique_count,
                "pooled_total": pooled_total,
                "top_count": top_count,
                "top_share": top_share,
                "diversity_ratio": diversity_ratio,
            },
        },
        statistics={
            "non_empty_count": pooled_total,
            "candidate_count": total_candidates or None,
            "unique_count": unique_count,
            "top_share": top_share,
            "margin": margin,
            "file_count": len(dataset.responses),
            "files_with_data": files_with_data,
            "consistency_agreement": agreement if files_with_data >= 2 else None,
            "per_file": per_file,
        },
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
