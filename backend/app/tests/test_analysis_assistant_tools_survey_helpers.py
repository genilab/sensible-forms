from __future__ import annotations

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.utils.survey_helpers import (
    extract_long_response_value,
    known_question_ids,
    resolve_question_text,
)


# survey_helpers: resolves question text from the questions CSV and enumerates known question ids.
def test_survey_helpers_resolve_question_text_and_known_ids():
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[
            {"question_id": "Q1", "question_text": "How are you?"},
            {"question_id": "Q2", "question_text": ""},
        ],
        label=None,
    )
    resp = CSVFile(id="r", columns=["Q1", "Q2"], rows=[], label=None)

    dataset = SurveyDataset(
        id="d",
        questions=questions,
        responses=[resp],
        join_key_questions="question_id",
        join_key_responses=None,
        responses_wide=True,
    )

    assert resolve_question_text(dataset, "Q1") == "How are you?"
    assert resolve_question_text(dataset, "Q2") is None

    ids = known_question_ids(dataset)
    assert "Q1" in ids
    assert "Q2" in ids


# extract_long_response_value: prefers standard long-format response fields in priority order.
def test_extract_long_response_value_prefers_standard_fields():
    assert extract_long_response_value({"answer": "x"}) == ("answer", "x")
    assert extract_long_response_value({"value": 10}) == ("value", 10)
    assert extract_long_response_value({"response": "y", "answer": "x"}) == ("response", "y")
    assert extract_long_response_value({"other": "z"}) == (None, None)
