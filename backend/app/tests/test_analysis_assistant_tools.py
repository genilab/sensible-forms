from __future__ import annotations

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.aggregateCategoricalInsight import (
    aggregate_categorical_question_insight,
)
from app.domains.analysis_assistant.tools.aggregateNumericInsight import (
    aggregate_numeric_question_insight,
)
from app.domains.analysis_assistant.tools.numAggregation import (
    aggregate_column,
    aggregate_column_multi,
)


class _Runtime:
    def __init__(self, tool_call_id: str = "t1") -> None:
        self.tool_call_id = tool_call_id


def test_aggregate_column_errors_and_success():
    csv = CSVFile(
        id="c1",
        columns=["x", "y"],
        rows=[{"x": "1"}, {"x": "2"}, {"x": "nope"}],
        label=None,
    )
    state = {"csv_data": [csv]}

    missing_csv = aggregate_column.func(csv_id="missing", column="x", operation="mean", state=state)
    assert missing_csv["result"] is None
    assert "not found" in missing_csv["error"].lower()

    missing_col = aggregate_column.func(csv_id="c1", column="missing", operation="mean", state=state)
    assert missing_col["result"] is None
    assert "column" in missing_col["error"].lower()

    bad_op = aggregate_column.func(csv_id="c1", column="x", operation="sum", state=state)
    assert bad_op["result"] is None
    assert "unsupported" in bad_op["error"].lower()

    ok = aggregate_column.func(csv_id="c1", column="x", operation="mean", state=state)
    assert ok["result"] == 1.5
    assert 0.0 <= ok["confidence"] <= 1.0
    assert ok["stats"]["numeric_count"] == 2


def test_aggregate_column_multi_errors_and_success():
    c1 = CSVFile(id="c1", columns=["x"], rows=[{"x": "1"}, {"x": "2"}], label=None)
    c2 = CSVFile(id="c2", columns=["x"], rows=[{"x": "3"}, {"x": "4"}], label=None)
    state = {"csv_data": [c1, c2]}

    no_ids = aggregate_column_multi.func(csv_ids=[], column="x", operation="mean", state=state)
    assert no_ids["result"] is None
    assert "no csv_ids" in no_ids["error"].lower()

    missing_csv = aggregate_column_multi.func(csv_ids=["c1", "missing"], column="x", operation="mean", state=state)
    assert missing_csv["result"] is None
    assert "not found" in missing_csv["error"].lower()

    missing_col = aggregate_column_multi.func(csv_ids=["c1", "c2"], column="y", operation="mean", state=state)
    assert missing_col["result"] is None
    assert "missing" in missing_col["error"].lower()

    ok = aggregate_column_multi.func(csv_ids=["c1", "c2"], column="x", operation="mean", state=state)
    assert ok["result"] == 2.5
    assert ok["stats"]["file_count"] == 2
    assert ok["stats"]["numeric_count"] == 4


def test_aggregate_numeric_question_insight_wide_and_errors():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "Satisfaction"}],
        label=None,
    )
    r1 = CSVFile(id="r1", columns=["Q1"], rows=[{"Q1": "1"}, {"Q1": "2"}], label=None)
    r2 = CSVFile(id="r2", columns=["Q1"], rows=[{"Q1": "3"}], label=None)
    dataset = SurveyDataset(
        id="d1",
        questions=questions,
        responses=[r1, r2],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )

    # Dataset not found
    cmd_nf = aggregate_numeric_question_insight.func(
        dataset_id="missing",
        question_id="Q1",
        operation="mean",
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )
    assert "No dataset" in cmd_nf.update["messages"][0].content

    # Unsupported operation
    cmd_bad_op = aggregate_numeric_question_insight.func(
        dataset_id="d1",
        question_id="Q1",
        operation="sum",
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )
    assert "Unsupported operation" in cmd_bad_op.update["messages"][0].content

    # Success
    cmd = aggregate_numeric_question_insight.func(
        dataset_id="d1",
        question_id="Q1",
        operation="mean",
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )
    assert "mean" in cmd.update["messages"][0].content
    insight = cmd.update["insights"][0]
    assert insight.insight_type == "numeric_aggregation"
    assert insight.evidence["question_id"] == "Q1"
    assert insight.statistics["numeric_count"] == 3


def test_aggregate_categorical_question_insight_wide_variants():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "Favorite color"}],
        label=None,
    )

    # Clear mode
    r = CSVFile(
        id="r",
        columns=["Q1"],
        rows=[
            {"Q1": "Blue"},
            {"Q1": "Blue"},
            {"Q1": "Red"},
            {"Q1": "N/A"},
        ],
        label=None,
    )
    dataset = SurveyDataset(
        id="d1",
        questions=questions,
        responses=[r],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )

    cmd = aggregate_categorical_question_insight.func(
        dataset_id="d1",
        question_id="Q1",
        top_k=3,
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )
    msg = cmd.update["messages"][0].content
    assert "most common" in msg
    insight = cmd.update["insights"][0]
    assert insight.insight_type == "categorical_distribution"
    assert insight.evidence["question_id"] == "Q1"

    # All unique branch
    r_unique = CSVFile(
        id="r2",
        columns=["Q1"],
        rows=[{"Q1": "a"}, {"Q1": "b"}, {"Q1": "c"}],
        label=None,
    )
    dataset_unique = SurveyDataset(
        id="d2",
        questions=questions,
        responses=[r_unique],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )

    cmd_unique = aggregate_categorical_question_insight.func(
        dataset_id="d2",
        question_id="Q1",
        top_k=3,
        state={"datasets": [dataset_unique]},
        runtime=_Runtime(),
    )
    assert "all responses are unique" in cmd_unique.update["messages"][0].content
