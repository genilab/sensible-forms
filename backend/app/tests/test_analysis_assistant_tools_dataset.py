from __future__ import annotations

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.createSurveyDataset import create_survey_dataset
from app.domains.analysis_assistant.tools.extractSurveyInsights import extract_survey_insights


class _Runtime:
    def __init__(self, tool_call_id: str = "t1") -> None:
        self.tool_call_id = tool_call_id


def test_create_survey_dataset_errors_and_wide_inference():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[
            {"question_id": "Q1", "question_text": "One"},
            {"question_id": "Q2", "question_text": "Two"},
        ],
        label=None,
    )
    responses = CSVFile(id="r", columns=["Q1", "Q2"], rows=[{"Q1": "x", "Q2": "y"}], label=None)
    state = {"csv_data": [questions, responses]}

    cmd_missing_q = create_survey_dataset.func(
        questions_csv_id="",
        response_csv_ids=["r"],
        join_key_questions="question_id",
        state=state,
        runtime=_Runtime(),
    )
    assert "required" in cmd_missing_q.update["messages"][0].content

    cmd_missing_r = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=[],
        join_key_questions="question_id",
        state=state,
        runtime=_Runtime(),
    )
    assert "empty" in cmd_missing_r.update["messages"][0].content

    # Ask for wide without passing response_question_columns; should infer from questions ids and response columns.
    cmd = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=["r"],
        join_key_questions="question_id",
        responses_wide=True,
        response_question_columns=None,
        state=state,
        runtime=_Runtime(),
    )

    ds: SurveyDataset = cmd.update["datasets"][0]
    assert ds.responses_wide is True
    assert ds.response_question_columns == ["Q1", "Q2"]


def test_create_survey_dataset_long_infers_join_key_responses_and_extract_insights_long_and_wide():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "One"}],
        label=None,
    )

    # Long responses: join_key_responses omitted; should infer it from join_key_questions since present.
    responses_long = CSVFile(
        id="r",
        columns=["question_id", "response"],
        rows=[
            {"question_id": "Q1", "response": "Yes"},
            {"question_id": "Q2", "response": "Should be skipped"},
            {"question_id": "", "response": "Skip"},
        ],
        label=None,
    )

    state = {"csv_data": [questions, responses_long], "datasets": []}

    cmd_ds = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=["r"],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=False,
        state=state,
        runtime=_Runtime(),
    )

    ds: SurveyDataset = cmd_ds.update["datasets"][0]
    assert ds.responses_wide is False
    assert ds.join_key_responses == "question_id"

    # Put dataset in state for extraction
    state2 = {"datasets": [ds]}
    cmd_ins = extract_survey_insights.func(dataset_id=ds.id, state=state2, runtime=_Runtime(), max_insights=250)
    assert "Extracted" in cmd_ins.update["messages"][0].content
    assert len(cmd_ins.update["insights"]) == 1

    # Wide extraction + cap
    responses_wide = CSVFile(
        id="rw",
        columns=["Q1"],
        rows=[{"Q1": "A"}, {"Q1": ""}, {"Q1": "B"}],
        label=None,
    )
    ds_wide = SurveyDataset(
        id="dw",
        questions=questions,
        responses=[responses_wide],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
        response_question_columns=["Q1"],
    )

    cmd_ins_w = extract_survey_insights.func(
        dataset_id=ds_wide.id,
        state={"datasets": [ds_wide]},
        runtime=_Runtime(),
        max_insights=1,
        max_rows_per_file=500,
    )
    assert "(capped)" in cmd_ins_w.update["messages"][0].content
    assert len(cmd_ins_w.update["insights"]) == 1


def test_create_survey_dataset_join_key_fallback_and_errors():
    # join_key_questions invalid but inferable
    questions = CSVFile(
        id="q",
        columns=["qid", "question_text"],
        rows=[{"qid": "Q1", "question_text": "One"}],
        label=None,
    )
    responses = CSVFile(id="r", columns=["qid", "response"], rows=[{"qid": "Q1", "response": "Yes"}], label=None)

    cmd = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=["r"],
        join_key_questions="question_id",  # not present; should fallback to qid
        responses_wide=False,
        state={"csv_data": [questions, responses]},
        runtime=_Runtime(),
    )
    ds: SurveyDataset = cmd.update["datasets"][0]
    assert ds.join_key_questions == "qid"
    assert ds.join_key_responses == "qid"

    # join_key_questions invalid and not inferable => error
    questions_no_ids = CSVFile(id="q2", columns=["text"], rows=[{"text": "One"}], label=None)
    responses_any = CSVFile(id="r2", columns=["x"], rows=[{"x": 1}], label=None)
    cmd_err = create_survey_dataset.func(
        questions_csv_id="q2",
        response_csv_ids=["r2"],
        join_key_questions="question_id",
        responses_wide=False,
        state={"csv_data": [questions_no_ids, responses_any]},
        runtime=_Runtime(),
    )
    assert "Unable to infer join key" in cmd_err.update["messages"][0].content


def test_create_survey_dataset_long_switches_to_wide_when_detected():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "One"}],
        label=None,
    )
    responses_wide = CSVFile(id="r", columns=["Q1"], rows=[{"Q1": "A"}], label=None)

    # Provide responses_wide=False and no join_key_responses; tool should detect wide columns and switch.
    cmd = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=["r"],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=False,
        state={"csv_data": [questions, responses_wide]},
        runtime=_Runtime(),
    )
    ds: SurveyDataset = cmd.update["datasets"][0]
    assert ds.responses_wide is True
    assert ds.response_question_columns == ["Q1"]


def test_create_survey_dataset_response_join_key_fallback_and_missing_error():
    questions = CSVFile(
        id="q",
        columns=["qid", "question_text"],
        rows=[{"qid": "Q1", "question_text": "One"}],
        label=None,
    )

    # join_key_responses missing, but fallback to qid_col present in responses
    responses = CSVFile(id="r", columns=["qid", "answer"], rows=[{"qid": "Q1", "answer": "Yes"}], label=None)
    cmd = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=["r"],
        join_key_questions="qid",
        join_key_responses="question_id",  # not present; should fallback
        responses_wide=False,
        state={"csv_data": [questions, responses]},
        runtime=_Runtime(),
    )
    ds: SurveyDataset = cmd.update["datasets"][0]
    assert ds.join_key_responses == "qid"

    # join_key_responses missing with no fallback => error
    responses_bad = CSVFile(id="r2", columns=["answer"], rows=[{"answer": "Yes"}], label=None)
    cmd_err = create_survey_dataset.func(
        questions_csv_id="q",
        response_csv_ids=["r2"],
        join_key_questions="qid",
        join_key_responses="question_id",
        responses_wide=False,
        state={"csv_data": [questions, responses_bad]},
        runtime=_Runtime(),
    )
    assert "missing join key" in cmd_err.update["messages"][0].content.lower()


def test_extract_survey_insights_dataset_not_found_returns_message():
    cmd = extract_survey_insights.func(dataset_id="missing", state={"datasets": []}, runtime=_Runtime())
    assert "No dataset found" in cmd.update["messages"][0].content


def test_extract_survey_insights_wide_caps_within_row_and_skips_missing_and_empty_cells():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "One"}, {"question_id": "Q2", "question_text": "Two"}],
        label="questions",
    )

    responses = CSVFile(
        id="r",
        columns=["Q1", "Q2"],
        rows=[
            {"Q1": "A", "Q2": "B"},  # would create 2 insights, but we'll cap
            {"Q1": "", "Q2": "C"},  # empty value should be skipped
            {"Q1": "D"},  # missing Q2 should be skipped
        ],
        label="responses",
    )

    ds = SurveyDataset(
        id="d",
        questions=questions,
        responses=[responses],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
        response_question_columns=["Q1", "Q2", "Q3"],  # Q3 not in row
    )

    cmd = extract_survey_insights.func(
        dataset_id="d",
        state={"datasets": [ds]},
        runtime=_Runtime(),
        max_insights=1,  # forces cap inside the qid loop
        max_rows_per_file=500,
    )

    assert "(capped)" in cmd.update["messages"][0].content
    assert len(cmd.update["insights"]) == 1
    ev = cmd.update["insights"][0].evidence
    assert ev["column"] in {"Q1", "Q2"}


def test_extract_survey_insights_long_handles_missing_question_lookup_and_skips_bad_rows():
    # join_key_questions is empty => q_lookup stays empty, and we should not filter by q_lookup membership.
    questions = CSVFile(id="q", columns=["question_id"], rows=[{"question_id": "Q1"}], label="questions")

    responses = CSVFile(
        id="r",
        columns=["question_id", "answer"],
        rows=[
            {"question_id": "", "answer": "skip-empty-qid"},
            {"question_id": "Q1"},  # no response/answer/value => skipped
            {"question_id": "Q1", "answer": "Yes"},
        ],
        label="responses",
    )

    ds = SurveyDataset(
        id="d2",
        questions=questions,
        responses=[responses],
        join_key_questions="",
        join_key_responses="question_id",
        responses_wide=False,
    )

    cmd = extract_survey_insights.func(
        dataset_id="d2",
        state={"datasets": [ds]},
        runtime=_Runtime(),
        max_insights=250,
        max_rows_per_file=500,
    )

    assert "Extracted 1 insights" in cmd.update["messages"][0].content
    assert len(cmd.update["insights"]) == 1
    ev = cmd.update["insights"][0].evidence
    assert ev["field"] == "answer"
