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

    Supports both response layouts:
    - wide responses: question id corresponds to a column
    - long/tidy responses: question id is stored in ``join_key_responses`` and the
      response value is taken from common fields (response/answer/value)

    Produces:
    - top-k counts + proportions
    - evidence samples: (csv_id, row_index, column/field, value)
    - confidence: derived from sample size/coverage/dominance and cross-file consistency

    Args:
        dataset_id: Dataset id in ``state["datasets"]``.
        question_id: User reference to a question (id/label/partial); resolved deterministically.
        top_k: Maximum number of categorical values to include (clamped to a small range).
        state: LangGraph-injected state dict.
        runtime: Tool runtime injected by ToolNode.

    Returns:
        A ``Command`` update that appends an ``Insight`` to ``state["insights"]`` and emits a
        user-visible ``ToolMessage``. On validation failures, returns a ToolMessage and no Insight.
    """

    # ---- 1) Validate tool runtime + locate the dataset in state ----
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

    # ---- 2) Resolve user question reference to a concrete question id / column ----
    # Users may refer to questions by label, partial ids, etc.; resolve conservatively
    # to a known question id/column so the rest of this tool can be deterministic.
    resolved_qid = resolve_question_id(user_ref=str(question_id), known_ids=known_question_ids(dataset))

    # ---- 3) Clamp top_k (maximum number of answers to include) to a small, safe range ----
    # Prevent huge outputs and keep the insight readable.
    k = max(1, min(int(top_k or 5), 8))

    # ---- 4) Initialize pooled aggregations across *all* response CSVs ----
    # We normalize categorical values (trim + lowercase) so that variants like
    # "Yes", " yes ", and "YES" are counted together.
    pooled_counter: Counter[str] = Counter()
    pooled_display: dict[str, str] = {}

    # Evidence buckets: normalized_value -> list[evidence]
    # We keep a few example rows for each value so downstream UI/LLM can cite sources.
    evidence_samples: dict[str, list[dict]] = defaultdict(list)

    # Coverage counters:
    # - candidates: how many rows *could* contain an answer for this question
    # - non_empty: how many actually contain a non-empty-ish answer
    total_candidates = 0
    total_non_empty = 0

    # Per-file stats are used for confidence scoring + cross-file consistency checks.
    per_file: list[dict] = []

    for resp_csv in dataset.responses:
        file_counter: Counter[str] = Counter()
        file_display: dict[str, str] = {}
        candidates = 0
        non_empty = 0
        missing_column = False
        missing_join_key = False

        if dataset.responses_wide:
            # ---- 5) Aggregate within a single response CSV ----
            # We compute per-file counters first, then merge into pooled counters.
            if resolved_qid not in (resp_csv.columns or []):
                missing_column = True
            else:
                for idx, row in enumerate(resp_csv.rows):
                    candidates += 1
                    raw = row.get(resolved_qid)
                    if _is_emptyish(raw):
                        continue
                # Wide responses: each question is a column (Q1, Q2, ...), each row is a respondent.
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
        # long/tidy format: look for question_id column to match resolved_qid, then extract response value from the same row.
        else:   
            qcol = dataset.join_key_responses or ""
            if not qcol or qcol not in (resp_csv.columns or []):
                missing_join_key = True
            else:
                for idx, row in enumerate(resp_csv.rows):
                    if str(row.get(qcol)) != str(resolved_qid):
                        continue
                # Long/tidy responses: each row is typically (question_id, response) for a respondent.
                # The join key identifies which question a given row belongs to.
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

        # ---- 6) Merge per-file counts into pooled counts ----
        pooled_counter.update(file_counter)
        for n, disp in file_display.items():
            pooled_display.setdefault(n, disp)

        # ---- 7) Compute per-file dominance + confidence diagnostics ----
        # This feeds the global confidence score and helps diagnose partial/messy data.
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

    # ---- 8) If nothing usable was found, return a tool message (no Insight) ----
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

    # ---- 9) Compute pooled (cross-file) top-k distribution ----
    pooled_total = sum(pooled_counter.values())
    top = pooled_counter.most_common(k)

    # Dominance stats describe whether there is a clear "mode" response.
    top_norm, top_count = top[0]
    top_share = top_count / pooled_total if pooled_total else 0.0

    unique_count = len(pooled_counter)

    second_share = 0.0
    if pooled_total and len(pooled_counter) >= 2:
        second_count = pooled_counter.most_common(2)[1][1]
        second_share = second_count / pooled_total
    margin = max(0.0, top_share - second_share)

    # ---- 10) Consistency across files ----
    # If multiple response CSVs exist, agreement on the global top response increases confidence.
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

    # ---- 11) Compute overall confidence score ----
    confidence = score_categorical_distribution(
        non_empty_count=pooled_total,
        candidate_count=total_candidates or None,
        top_share=top_share,
        margin=margin,
        consistency_score=consistency_score if files_with_data >= 2 else None,
    )

    # Prefer human-readable question text when we can resolve it.
    question_text = resolve_question_text(dataset, resolved_qid)
    question_label = question_text or f"Question {resolved_qid}"

    # ---- 12) Build the top-k payload with evidence ----
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

    # ---- 13) Adapt the summary for open-ended / high-diversity distributions ----
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

    # ---- 14) Materialize Insight + return Command update ----
    # The graph runtime merges `insights`/`messages` into state.
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
