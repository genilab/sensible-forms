from __future__ import annotations

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.aggregateCategoricalInsight import (
    aggregate_categorical_question_insight,
)
from app.domains.analysis_assistant.tools.aggregateNumericInsight import (
    _weighted_mean,
    _weighted_variance,
    aggregate_numeric_question_insight,
)
from app.domains.analysis_assistant.tools.numAggregation import (
    aggregate_column,
    aggregate_column_multi,
)


class _Runtime:
    def __init__(self, tool_call_id: str = "t1") -> None:
        self.tool_call_id = tool_call_id


def _questions_csv(*, qid: str = "Q1", text: str = "Question") -> CSVFile:
    return CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": qid, "question_text": text}],
        label="questions",
    )


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


def test_weighted_mean_and_variance_return_zero_when_all_weights_are_zero():
    pairs = [(10.0, 0.0), (20.0, 0.0)]
    m = _weighted_mean(pairs)
    assert m == 0.0
    assert _weighted_variance(pairs, m) == 0.0


def test_aggregate_numeric_question_insight_wide_and_errors():
    questions = _questions_csv(qid="Q1", text="Satisfaction")
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


def test_aggregate_numeric_question_insight_wide_missing_column_and_no_numeric_values():
    questions = _questions_csv(qid="Q1", text="Satisfaction")

    # r1 has the column but no numeric values; r2 is missing the column entirely.
    r1 = CSVFile(id="r1", columns=["Q1"], rows=[{"Q1": "n/a"}, {"Q1": ""}], label="responses")
    r2 = CSVFile(id="r2", columns=["Other"], rows=[{"Other": "1"}], label="responses")

    dataset = SurveyDataset(
        id="d",
        questions=questions,
        responses=[r1, r2],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )

    cmd = aggregate_numeric_question_insight.func(
        dataset_id="d",
        question_id="Q1",
        operation="mean",
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )

    assert "No numeric values" in cmd.update["messages"][0].content


def test_aggregate_numeric_question_insight_long_computes_consistency_and_handles_missing_join_key():
    questions = _questions_csv(qid="Q1", text="Score")

    r_ok_1 = CSVFile(
        id="r1",
        columns=["question_id", "response"],
        rows=[
            {"question_id": "Q1", "response": "1"},
            {"question_id": "Q1", "response": "2"},
            {"question_id": "Q2", "response": "999"},  # ignored
        ],
        label="responses",
    )
    r_ok_2 = CSVFile(
        id="r2",
        columns=["question_id", "answer"],
        rows=[
            {"question_id": "Q1", "answer": "10"},
            {"question_id": "Q1", "answer": "11"},
        ],
        label="responses",
    )
    r_missing_key = CSVFile(
        id="r3",
        columns=["not_question_id", "response"],
        rows=[{"not_question_id": "Q1", "response": "5"}],
        label="responses",
    )

    dataset = SurveyDataset(
        id="d",
        questions=questions,
        responses=[r_ok_1, r_ok_2, r_missing_key],
        join_key_questions="question_id",
        join_key_responses="question_id",
        responses_wide=False,
    )

    cmd = aggregate_numeric_question_insight.func(
        dataset_id="d",
        question_id="Q1",
        operation="mean",
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )

    insight = cmd.update["insights"][0]
    stats = insight.statistics
    assert stats["files_with_numeric"] == 2
    assert isinstance(stats.get("consistency"), dict)
    assert len(stats["per_file"]) == 3
    assert any(item.get("stats", {}).get("missing_join_key") for item in stats["per_file"])


def test_aggregate_categorical_question_insight_wide_variants():
    questions = _questions_csv(qid="Q1", text="Favorite color")

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


def test_aggregate_categorical_question_insight_wide_rejects_all_emptyish_values_including_none():
    questions = _questions_csv(qid="Q1", text="Favorite")
    responses = CSVFile(
        id="r",
        columns=["Q1"],
        rows=[
            {"Q1": None},
            {"Q1": ""},
            {"Q1": "N/A"},
            {"Q1": "prefer not to say"},
        ],
        label="responses",
    )
    dataset = SurveyDataset(
        id="d",
        questions=questions,
        responses=[responses],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )

    cmd = aggregate_categorical_question_insight.func(
        dataset_id="d",
        question_id="Q1",
        top_k=5,
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )
    assert "No non-empty categorical values" in cmd.update["messages"][0].content


def test_aggregate_categorical_question_insight_long_includes_field_evidence_and_missing_join_key_stats():
    questions = _questions_csv(qid="Q1", text="Color")

    r_ok = CSVFile(
        id="r1",
        columns=["question_id", "value"],
        rows=[
            {"question_id": "Q1", "value": "Blue"},
            {"question_id": "Q1", "value": "blue"},
            {"question_id": "Q1", "value": "Red"},
        ],
        label="responses",
    )
    r_missing_key = CSVFile(
        id="r2",
        columns=["qid", "value"],
        rows=[{"qid": "Q1", "value": "Blue"}],
        label="responses",
    )

    dataset = SurveyDataset(
        id="d",
        questions=questions,
        responses=[r_ok, r_missing_key],
        join_key_questions="question_id",
        join_key_responses="question_id",
        responses_wide=False,
    )

    cmd = aggregate_categorical_question_insight.func(
        dataset_id="d",
        question_id="Q1",
        top_k=100,  # exercise clamp-to-10
        state={"datasets": [dataset]},
        runtime=_Runtime(),
    )

    insight = cmd.update["insights"][0]
    assert len(insight.evidence["top_values"]) <= 10

    # Evidence items in long mode should include a 'field' key.
    ev = insight.evidence["top_values"][0]["evidence"]
    assert any("field" in e for e in ev)

    per_file = insight.statistics["per_file"]
    assert len(per_file) == 2
    assert any(item.get("stats", {}).get("missing_join_key") for item in per_file)


def test_aggregate_categorical_question_insight_mostly_unique_and_minor_mode_summaries():
    questions = _questions_csv(qid="Q1", text="Open ended")

    # Mostly-unique: 10 responses, 9 unique, top frequency 2.
    mostly_unique_rows = [{"Q1": f"v{i}"} for i in range(1, 10)] + [{"Q1": "v1"}]
    r1 = CSVFile(id="r1", columns=["Q1"], rows=mostly_unique_rows, label="responses")
    d1 = SurveyDataset(
        id="d1",
        questions=questions,
        responses=[r1],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )
    cmd1 = aggregate_categorical_question_insight.func(
        dataset_id="d1",
        question_id="Q1",
        state={"datasets": [d1]},
        runtime=_Runtime(),
    )
    assert "highly diverse with no clear consensus" in cmd1.update["messages"][0].content

    # Minor mode: 12 responses, still diverse, but a "top" exists.
    minor_mode_rows = [
        {"Q1": "top"},
        {"Q1": "top"},
        {"Q1": "top"},
        {"Q1": "a"},
        {"Q1": "b"},
        {"Q1": "c"},
        {"Q1": "d"},
        {"Q1": "e"},
        {"Q1": "f"},
        {"Q1": "g"},
        {"Q1": "h"},
        {"Q1": "i"},
    ]
    r2 = CSVFile(id="r2", columns=["Q1"], rows=minor_mode_rows, label="responses")
    d2 = SurveyDataset(
        id="d2",
        questions=questions,
        responses=[r2],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )
    cmd2 = aggregate_categorical_question_insight.func(
        dataset_id="d2",
        question_id="Q1",
        state={"datasets": [d2]},
        runtime=_Runtime(),
    )
    assert "but responses are still highly diverse" in cmd2.update["messages"][0].content
