from __future__ import annotations

import math
from typing import Any, Dict, Optional


# Lower bound used across deterministic/scored insights.
# We avoid hard 0.0 to reduce brittleness while still signaling low confidence.
MINIMUM_CONFIDENCE_SCORE = 0.05

# Upper bound used across deterministic/scored insights.
# We avoid hard 1.0 to reduce brittleness.
MAXIMUM_CONFIDENCE_SCORE = 0.95


_DEFAULT_QUESTION_TEXT_KEYS = ["question", "question_text", "text", "prompt", "label"]


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _norm_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_non_answer(value: Any) -> bool:
    s = _norm_str(value)
    if not s:
        return True

    non_answers = {
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
    return s in non_answers


def score_response_summary(
    *,
    response_value: Any,
    question_row: Optional[Dict[str, Any]] = None,
    source_field: Optional[str] = None,
    is_wide: bool,
) -> float:
    """
    Deterministic confidence score for "response_summary" insights.

    This is intentionally heuristic (not statistical). It favors:
    - responses that can be linked to a known question row
    - responses coming from an expected field/column
    - responses that are not placeholders like "N/A"

    Returns a value in [0, 1].
    """

    # Base: we have *some* evidence (a cell value in a known CSV row)
    score = 0.45

    if question_row is not None:
        score += 0.20

        # If the question row appears to contain a readable question text, boost a bit
        if any((k in question_row and str(question_row.get(k) or "").strip()) for k in _DEFAULT_QUESTION_TEXT_KEYS):
            score += 0.10

    # Prefer canonical fields/columns for response values
    if is_wide:
        # In wide format the column itself is the question id
        score += 0.10
    else:
        # In long format, reward standard response column names
        if (source_field or "") in {"response", "answer", "value"}:
            score += 0.10
        elif source_field:
            score += 0.05

    # Penalize placeholders / missing-ish values
    if _is_non_answer(response_value):
        score -= 0.35

    # Tiny answers are often low-signal (unless it's a scale, which we can't infer safely)
    resp_str = str(response_value).strip() if response_value is not None else ""
    if 0 < len(resp_str) <= 1:
        score -= 0.10

    # Very long free-text is valid, but more ambiguous for "summary" purposes
    if len(resp_str) > 500:
        score -= 0.05

    # Keep in a sensible band; avoid absolute 0/1 to reduce brittleness.
    score = min(MAXIMUM_CONFIDENCE_SCORE, max(MINIMUM_CONFIDENCE_SCORE, score))
    return clamp01(score)


def score_numeric_aggregation(
    *,
    numeric_count: int,
    row_count: Optional[int],
    operation: str,
) -> float:
    """
    Data-driven confidence for numeric aggregations.

    Uses only information the aggregation tool already has (counts + operation).
    Key ideas:
    - More numeric samples => higher confidence (saturating)
    - Higher numeric coverage of the column => higher confidence
    - Min/Max are more sensitive to outliers, so slightly lower confidence

    Returns a value in [0, 1].
    """

    n = max(0, int(numeric_count or 0))
    rc = row_count if (row_count is not None and row_count > 0) else None

    if n == 0:
        return MINIMUM_CONFIDENCE_SCORE

    # Sample size confidence: saturates toward 1 as n grows.
    # n=10 -> ~0.33, n=30 -> ~0.70, n=60 -> ~0.90
    size_score = 1.0 - math.exp(-n / 25.0)

    # Coverage confidence: how much of the dataset is usable numerically.
    # If row_count is unknown, treat coverage as neutral-high.
    coverage = (n / rc) if rc else 0.85
    coverage = max(0.0, min(1.0, coverage))

    op = (operation or "").strip().lower()
    op_weight = 1.0
    if op in {"min", "max"}:
        op_weight = 0.88
    elif op in {"mean", "median"}:
        op_weight = 1.0
    else:
        op_weight = 0.92

    # Combine: base + weighted size + weighted coverage.
    score = 0.15 + 0.55 * size_score + 0.30 * coverage
    score *= op_weight

    # Very small n is fragile; clamp down.
    if n < 3:
        score *= 0.65
    elif n < 10:
        score *= 0.85

    score = min(MAXIMUM_CONFIDENCE_SCORE, max(MINIMUM_CONFIDENCE_SCORE, score))
    return clamp01(score)


def score_categorical_distribution(
    *,
    non_empty_count: int,
    candidate_count: Optional[int],
    top_share: float,
    margin: float,
    consistency_score: Optional[float] = None,
) -> float:
    """Data-driven confidence for categorical/text response distributions.

    Inputs:
    - non_empty_count: number of usable (non-empty) answers
    - candidate_count: number of candidate rows considered (for coverage)
    - top_share: share of the most common answer in [0,1]
    - margin: (top_share - second_share) in [0,1]
    - consistency_score: optional cross-file stability in [0,1]

    Returns a value in [0,1].
    """

    n = max(0, int(non_empty_count or 0))
    if n == 0:
        return MINIMUM_CONFIDENCE_SCORE

    # Sample size saturating curve
    size_score = 1.0 - math.exp(-n / 25.0)

    # Coverage: fraction of candidate rows that are usable
    if candidate_count is not None and candidate_count > 0:
        coverage = n / candidate_count
    else:
        coverage = 0.85
    coverage = max(0.0, min(1.0, float(coverage)))

    ts = max(0.0, min(1.0, float(top_share)))
    mg = max(0.0, min(1.0, float(margin)))

    # Base combination: size + coverage + effect strength (dominance + margin)
    score = 0.12 + 0.45 * size_score + 0.25 * coverage + 0.18 * ts + 0.10 * mg

    # Very small n is fragile
    if n < 3:
        score *= 0.65
    elif n < 10:
        score *= 0.85

    # If cross-file consistency is provided, blend it in
    if consistency_score is not None:
        cs = max(0.0, min(1.0, float(consistency_score)))
        score *= (0.60 + 0.40 * cs)

    score = min(MAXIMUM_CONFIDENCE_SCORE, max(MINIMUM_CONFIDENCE_SCORE, score))
    return clamp01(score)
