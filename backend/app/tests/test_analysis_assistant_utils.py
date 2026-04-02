from __future__ import annotations

from app.domains.analysis_assistant.tools.utils.confidence import (
    score_categorical_distribution,
    score_numeric_aggregation,
    score_response_summary,
)
from app.domains.analysis_assistant.tools.utils.dataset_inference import (
    detect_wide_response_columns,
    find_question_id_column,
)
from app.domains.analysis_assistant.tools.utils.number_parse import try_parse_float
from app.domains.analysis_assistant.tools.utils.question_resolve import resolve_question_id
from app.domains.analysis_assistant.structs.csvFile import CSVFile


def test_try_parse_float_handles_common_cases():
    assert try_parse_float(None) is None
    assert try_parse_float(4) == 4.0
    assert try_parse_float(4.25) == 4.25

    assert try_parse_float(" 4 ") == 4.0
    assert try_parse_float("1,234") == 1234.0
    assert try_parse_float("42%") == 42.0
    assert try_parse_float("4 - Agree") == 4.0

    assert try_parse_float("") is None
    assert try_parse_float("   ") is None
    assert try_parse_float("nope") is None


def test_score_response_summary_rewards_question_row_and_penalizes_non_answers():
    baseline = score_response_summary(response_value="Yes", question_row=None, source_field=None, is_wide=False)

    with_question = score_response_summary(
        response_value="Yes",
        question_row={"question_text": "How are you?"},
        source_field="response",
        is_wide=False,
    )
    assert with_question > baseline

    non_answer = score_response_summary(
        response_value="N/A",
        question_row={"question_text": "How are you?"},
        source_field="response",
        is_wide=False,
    )
    assert non_answer < with_question

    # Always stays within [0, 1]
    assert 0.0 <= non_answer <= 1.0


def test_score_numeric_aggregation_behaves_sensibly():
    none = score_numeric_aggregation(numeric_count=0, row_count=10, operation="mean")
    assert none == 0.05

    small = score_numeric_aggregation(numeric_count=2, row_count=10, operation="mean")
    bigger = score_numeric_aggregation(numeric_count=30, row_count=40, operation="mean")
    assert bigger > small

    min_score = score_numeric_aggregation(numeric_count=30, row_count=40, operation="min")
    mean_score = score_numeric_aggregation(numeric_count=30, row_count=40, operation="mean")
    assert mean_score >= min_score


def test_score_categorical_distribution_increases_with_samples_and_consistency():
    none = score_categorical_distribution(
        non_empty_count=0,
        candidate_count=10,
        top_share=0.5,
        margin=0.2,
        consistency_score=None,
    )
    assert none == 0.05

    low = score_categorical_distribution(
        non_empty_count=5,
        candidate_count=10,
        top_share=0.5,
        margin=0.1,
        consistency_score=0.2,
    )
    high = score_categorical_distribution(
        non_empty_count=50,
        candidate_count=60,
        top_share=0.7,
        margin=0.3,
        consistency_score=0.9,
    )
    assert high > low


def test_find_question_id_column_prefers_priority_names():
    assert find_question_id_column(["qid", "x"]) == "qid"
    assert find_question_id_column(["question_id"]) == "question_id"
    assert find_question_id_column(["id"]) == "id"
    assert find_question_id_column(["something_else"]) is None


def test_detect_wide_response_columns_intersection_then_union_fallback():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[
            {"question_id": "Q1", "question_text": "One"},
            {"question_id": "Q2", "question_text": "Two"},
            {"question_id": "Q3", "question_text": "Three"},
        ],
        label=None,
    )

    r1 = CSVFile(id="r1", columns=["Q1", "Q2", "junk"], rows=[], label=None)
    r2 = CSVFile(id="r2", columns=["Q2", "Q3"], rows=[], label=None)

    # Intersection contains only Q2
    assert detect_wide_response_columns(questions, [r1, r2]) == ["Q2"]

    # If intersection is empty, union is returned
    r3 = CSVFile(id="r3", columns=["Q1"], rows=[], label=None)
    r4 = CSVFile(id="r4", columns=["Q3"], rows=[], label=None)
    assert detect_wide_response_columns(questions, [r3, r4]) == ["Q1", "Q3"]


def test_resolve_question_id_is_conservative():
    known = {"Q1", "q2", "Question 3"}

    # Exact match
    assert resolve_question_id(user_ref="Q1", known_ids=known) == "Q1"

    # Case-insensitive match
    assert resolve_question_id(user_ref="Q2", known_ids=known) == "q2"

    # Numeric resolution
    assert resolve_question_id(user_ref="question 3", known_ids=known) == "Question 3"

    # Ambiguous numeric match => unchanged
    ambiguous = {"Q1", "Question 1"}
    assert resolve_question_id(user_ref="1", known_ids=ambiguous) == "1"


def test_resolve_question_id_additional_branches():
    # Empty/whitespace input
    assert resolve_question_id(user_ref="   ", known_ids={"Q1"}) == ""

    # No digits and no exact match => unchanged
    assert resolve_question_id(user_ref="alpha", known_ids={"Q1"}) == "alpha"

    # Ambiguous numeric matches, but a single preferred short form exists.
    # digit_matches: ["Item 1", "Q1"], preferred: ["Q1"]
    known = {"Item 1", "Q1"}
    assert resolve_question_id(user_ref="1", known_ids=known) == "Q1"

    # Unique numeric digit match (no exact/CI match), e.g. "q3" -> "Question 3".
    assert resolve_question_id(user_ref="q3", known_ids={"Question 3"}) == "Question 3"

    # Digits present but no known id matches => unchanged.
    assert resolve_question_id(user_ref="q9", known_ids={"Q1"}) == "q9"
