from __future__ import annotations

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset


# CSVFile struct: validates convenience properties/helpers (num_rows, sample, column_values).
def test_csvfile_helpers():
    csv_file = CSVFile(
        id="c1",
        columns=["a", "b"],
        rows=[{"a": 1, "b": 2}, {"a": 3}],
        label=None,
    )
    assert csv_file.num_rows == 2
    assert csv_file.sample(1) == [{"a": 1, "b": 2}]
    assert csv_file.column_values("a") == [1, 3]
    assert csv_file.column_values("b") == [2]


# SurveyDataset struct: validates schema checks for long vs wide response layouts.
def test_survey_dataset_validate_long_and_wide():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "One"}],
        label=None,
    )

    # Long format: requires join_key_responses column in each response file
    resp_ok = CSVFile(id="r1", columns=["question_id", "response"], rows=[], label=None)
    ds_long = SurveyDataset(
        id="ds",
        questions=questions,
        responses=[resp_ok],
        join_key_questions="question_id",
        join_key_responses="question_id",
        responses_wide=False,
    )
    out_long = ds_long.validate()
    assert out_long["valid"] is True

    resp_bad = CSVFile(id="r2", columns=["qid", "response"], rows=[], label=None)
    ds_long_bad = SurveyDataset(
        id="ds",
        questions=questions,
        responses=[resp_bad],
        join_key_questions="question_id",
        join_key_responses="question_id",
        responses_wide=False,
    )
    out_long_bad = ds_long_bad.validate()
    assert out_long_bad["valid"] is False
    assert out_long_bad["missing_join_key"] == ["r2"]

    # Wide format: requires declared question columns to exist in each response file
    resp_wide = CSVFile(id="rw", columns=["Q1", "Q2"], rows=[], label=None)
    ds_wide = SurveyDataset(
        id="dsw",
        questions=questions,
        responses=[resp_wide],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
        response_question_columns=["Q1", "Q2"],
    )
    out_wide = ds_wide.validate()
    assert out_wide["valid"] is True

    resp_wide_bad = CSVFile(id="rw2", columns=["Q1"], rows=[], label=None)
    ds_wide_bad = SurveyDataset(
        id="dsw",
        questions=questions,
        responses=[resp_wide_bad],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
        response_question_columns=["Q1", "Q2"],
    )
    out_wide_bad = ds_wide_bad.validate()
    assert out_wide_bad["valid"] is False
    assert out_wide_bad["missing_join_key"] == ["rw2:Q2"]
