from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domains.analysis_assistant.nodes.ingestion_orchestrator import (
    _ensure_unique_label,
    make_ingestion_orchestrator_node,
)
from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset


@dataclass
class _FakeLLM:
    invoked: bool = False

    def invoke(self, messages, tools=None, max_output_tokens=None, temperature=None, config=None):
        self.invoked = True
        return AIMessage(content="ok")


@dataclass
class _CapturingLLM:
    invoked: bool = False
    last_messages: list | None = None

    def invoke(self, messages, tools=None, max_output_tokens=None, temperature=None, config=None):
        self.invoked = True
        self.last_messages = list(messages)
        return AIMessage(content="ok")


def test_ensure_unique_label_appends_suffixes():
    existing = {"responses", "responses_2"}
    assert _ensure_unique_label(existing, "questions") == "questions"
    assert _ensure_unique_label(existing, "responses") == "responses_3"


def test_ingestion_orchestrator_labels_and_creates_wide_dataset_deterministically():
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


def test_ingestion_orchestrator_llm_context_includes_candidates_and_unlabeled_previews():
    llm = _CapturingLLM()
    node = make_ingestion_orchestrator_node(llm)

    # Intentionally avoid deterministic labeling:
    # - questions CSV has only 'question_id' (not enough to infer 'questions')
    # - responses wide has only 2 Q* columns (not enough to infer 'responses')
    # - long responses has no respondent_id and <3 Q* columns
    questions_like = CSVFile(
        id="q",
        columns=["question_id"],
        rows=[{"question_id": "Q1"}, {"question_id": ""}, {"question_id": "Q2"}],
        label=None,
    )
    responses_wide_like = CSVFile(
        id="rw",
        columns=["Q1", "Q2", "x"],
        rows=[{"Q1": "1", "Q2": "2", "x": "z"}],
        label=None,
    )
    responses_long_like = CSVFile(
        id="rl",
        columns=["question_id", "value"],
        rows=[{"question_id": "Q1", "value": "yes"}],
        label=None,
    )

    out = node({"csv_data": [questions_like, responses_wide_like, responses_long_like], "datasets": [], "mode": None})

    assert llm.invoked is True
    assert "messages" in out
    assert len(out["messages"]) == 1

    # Validate the constructed context (covers many branches in the LLM-path).
    assert llm.last_messages is not None
    assert isinstance(llm.last_messages[0], SystemMessage)
    assert isinstance(llm.last_messages[1], HumanMessage)

    text = llm.last_messages[1].content
    assert "CSV files (trimmed):" in text
    assert "Candidate join keys (overlap):" in text
    assert "Question IDs sample" in text
    assert "Wide-format candidates:" in text
    assert "Response columns preview" in text
    assert "Unlabeled CSVs:" in text
