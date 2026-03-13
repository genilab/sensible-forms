from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage

from app.domains.analysis_assistant.nodes.ingestion_orchestrator import (
    _ensure_unique_label,
    make_ingestion_orchestrator_node,
)
from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.createSurveyDataset import create_survey_dataset
from app.domains.analysis_assistant.tools.extractSurveyInsights import extract_survey_insights


class _Runtime:
    def __init__(self, tool_call_id: str = "t1") -> None:
        self.tool_call_id = tool_call_id


@dataclass
class _FakeLLM:
    invoked: bool = False

    def invoke(self, messages, tools=None, max_output_tokens=None, temperature=None, config=None):
        self.invoked = True
        return AIMessage(content="ok")


def test_ensure_unique_label_appends_suffixes():
    existing = {"responses", "responses_2"}
    assert _ensure_unique_label(existing, "questions") == "questions"
    assert _ensure_unique_label(existing, "responses") == "responses_3"


def test_ingestion_orchestrator_labels_and_creates_wide_dataset_deterministically(monkeypatch):
    llm = _FakeLLM()
    node = make_ingestion_orchestrator_node(llm)

    questions = CSVFile(
        id="qcsv",
        columns=["question_id", "question_text", "question_type"],
        rows=[
            {"question_id": "Q1", "question_text": "One", "question_type": "scale"},
            {"question_id": "Q2", "question_text": "Two", "question_type": "scale"},
        ],
        label=None,
    )
    responses = CSVFile(
        id="rcsv",
        columns=["respondent_id", "Q1", "Q2"],
        rows=[{"respondent_id": "r1", "Q1": "1", "Q2": "2"}],
        label=None,
    )

    out = node({"csv_data": [questions, responses], "datasets": [], "mode": None})
    assert llm.invoked is False

    # labels are set in-place
    assert questions.label == "questions"
    assert responses.label.startswith("responses")

    assert "datasets" in out
    ds: SurveyDataset = out["datasets"][0]
    assert ds.responses_wide is True
    assert ds.join_key_questions in {"question_id", "qid", "questionId", "id"}
    assert ds.response_question_columns == ["Q1", "Q2"]


def test_ingestion_orchestrator_creates_long_dataset_deterministically():
    llm = _FakeLLM()
    node = make_ingestion_orchestrator_node(llm)

    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text", "question_type"],
        rows=[{"question_id": "Q1", "question_text": "One", "question_type": "text"}],
        label="questions",
    )
    responses = CSVFile(
        id="r",
        columns=["question_id", "response"],
        rows=[{"question_id": "Q1", "response": "Yes"}],
        label="responses",
    )

    out = node({"csv_data": [questions, responses], "datasets": [], "mode": None})
    assert llm.invoked is False
    ds: SurveyDataset = out["datasets"][0]
    assert ds.responses_wide is False
    assert ds.join_key_responses == "question_id"


def test_ingestion_orchestrator_upload_mode_does_not_call_llm_when_only_unlabeled():
    llm = _FakeLLM()
    node = make_ingestion_orchestrator_node(llm)

    unknown = CSVFile(id="u1", columns=["a", "b"], rows=[{"a": 1, "b": 2}], label=None)

    # Deterministic labeling cannot label this; upload mode should not trigger LLM.
    out = node({"csv_data": [unknown], "datasets": [], "mode": "upload"})
    assert out == {}
    assert llm.invoked is False


def test_ingestion_orchestrator_non_upload_calls_llm_when_needed():
    llm = _FakeLLM()
    node = make_ingestion_orchestrator_node(llm)

    unknown = CSVFile(id="u1", columns=["a", "b"], rows=[{"a": 1, "b": 2}], label=None)

    out = node({"csv_data": [unknown], "datasets": [], "mode": None})
    assert llm.invoked is True
    assert "messages" in out
    assert len(out["messages"]) == 1


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
