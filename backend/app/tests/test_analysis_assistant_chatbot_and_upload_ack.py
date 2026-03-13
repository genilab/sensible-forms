from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domains.analysis_assistant.nodes.chatbot import make_chatbot_node
from app.domains.analysis_assistant.nodes.upload_ack import upload_ack
from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.describeCSVs import describe_csv
from app.domains.analysis_assistant.tools.labelCSV import infer_label_for_csv, label_csv
from app.domains.analysis_assistant.tools.sampleRows import sample_rows


@dataclass
class _CapturingLLM:
    last_messages: list | None = None

    def invoke(self, messages, tools=None, max_output_tokens=None, temperature=None, config=None):
        self.last_messages = list(messages)
        return AIMessage(content="ok")


class _FailingLLM:
    def __init__(self, msg: str):
        self._msg = msg

    def invoke(self, messages, tools=None, max_output_tokens=None, temperature=None, config=None):
        raise Exception(self._msg)


def test_chatbot_injects_system_context_and_ensures_human_last():
    llm = _CapturingLLM()
    chatbot = make_chatbot_node(llm)

    csv1 = CSVFile(id="c1", columns=["a"], rows=[{"a": 1}], label="responses")
    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "One"}],
        label="questions",
    )
    ds = SurveyDataset(
        id="d1",
        questions=questions,
        responses=[csv1],
        join_key_questions="question_id",
        join_key_responses="question_id",
        responses_wide=False,
    )

    # Last message is AI, but we have last_user_prompt in state.
    out = chatbot(
        {
            "messages": [AIMessage(content="prev")],
            "csv_data": [csv1],
            "datasets": [ds],
            "last_user_prompt": "Help me analyze",
        }
    )

    assert out["mode"] is None
    assert out["messages"] and isinstance(out["messages"][0], AIMessage)

    assert llm.last_messages is not None
    assert isinstance(llm.last_messages[0], SystemMessage)
    sys_text = llm.last_messages[0].content
    assert "Available CSV files" in sys_text
    assert "responses (c1)" in sys_text
    assert "Survey datasets" in sys_text
    assert "d1" in sys_text

    # Provider requirement: last prompt should be HumanMessage
    assert isinstance(llm.last_messages[-1], HumanMessage)


def test_chatbot_handles_rate_limit_exceptions():
    chatbot = make_chatbot_node(_FailingLLM("429 RESOURCE_EXHAUSTED"))
    out = chatbot({"messages": [HumanMessage(content="hi")], "csv_data": [], "datasets": []})
    assert out["mode"] is None
    assert isinstance(out["messages"][0], AIMessage)
    assert "rate-limited" in out["messages"][0].content


def test_upload_ack_suppresses_ack_when_last_ai_is_non_upload_plain_text():
    out = upload_ack(
        {
            "mode": "upload",
            "messages": [HumanMessage(content="hi"), AIMessage(content="What is this file?")],
            "csv_data": [],
            "datasets": [],
            "last_user_prompt": "hi",
        }
    )
    assert out["mode"] is None
    assert "messages" not in out


def test_upload_ack_builds_ack_with_multiple_files_unlabeled_and_dataset_ready():
    c1 = CSVFile(id="c1", columns=["a"], rows=[{"a": 1}], label=None)
    c2 = CSVFile(id="c2", columns=["b"], rows=[{"b": 2}], label="responses")

    questions = CSVFile(
        id="q",
        columns=["question_id", "question_text"],
        rows=[{"question_id": "Q1", "question_text": "One"}],
        label="questions",
    )
    ds = SurveyDataset(
        id="d1",
        questions=questions,
        responses=[c2],
        join_key_questions="question_id",
        join_key_responses="question_id",
        responses_wide=False,
    )

    out = upload_ack(
        {
            "mode": "upload",
            "messages": [HumanMessage(content="upload")],
            "csv_data": [c1, c2],
            "datasets": [ds],
            "last_uploaded_csv_id": "c1",
        }
    )

    msg = out["messages"][0]
    assert isinstance(msg, AIMessage)
    text = msg.content

    assert "Thanks" in text
    assert "I now have access to 2 CSV files" in text
    assert "Unlabeled CSV" in text
    assert "Dataset ready" in text


def test_upload_ack_suggests_linking_when_two_files_and_no_dataset():
    c1 = CSVFile(id="c1", columns=["a"], rows=[{"a": 1}], label="questions")
    c2 = CSVFile(id="c2", columns=["b"], rows=[{"b": 2}], label="responses")

    out = upload_ack(
        {
            "mode": "upload",
            "messages": [HumanMessage(content="upload")],
            "csv_data": [c1, c2],
            "datasets": [],
            "last_uploaded_csv_id": "c2",
        }
    )

    text = out["messages"][0].content
    assert "link them into a dataset" in text


def test_label_csv_sets_label_and_infer_label_heuristics():
    q_csv = CSVFile(
        id="q",
        columns=["question_id", "question_text", "question_type"],
        rows=[],
        label=None,
    )
    assert infer_label_for_csv(q_csv) == "questions"

    resp_csv = CSVFile(id="r", columns=["respondent_id", "Q1"], rows=[], label=None)
    assert infer_label_for_csv(resp_csv) == "responses"

    wide_resp = CSVFile(id="w", columns=["Q1", "Q2", "Q3"], rows=[], label=None)
    assert infer_label_for_csv(wide_resp) == "responses"

    state = {"csv_data": [q_csv]}
    assert label_csv.func(csv_id="q", label="questions", state=state).startswith("CSV q labeled")
    assert q_csv.label == "questions"

    assert label_csv.func(csv_id="missing", label="x", state=state) == "CSV not found"


def test_label_csv_infer_label_additional_branches():
    # questionish intersection branch (>=3 question-ish columns)
    qish = CSVFile(id="qish", columns=["question_id", "scale_min", "scale_max"], rows=[], label=None)
    assert infer_label_for_csv(qish) == "questions"

    # unknown shape => None
    unknown = CSVFile(id="u", columns=["foo", "bar"], rows=[], label=None)
    assert infer_label_for_csv(unknown) is None


def test_describe_csv_and_sample_rows_tools():
    csv = CSVFile(
        id="c1",
        columns=["a", "b"],
        rows=[{"a": 1, "b": 2}, {"a": 3, "b": 4}],
        label=None,
    )
    state = {"csv_data": [csv]}

    # describe_csv: success + not found
    ok = describe_csv.func(csv_id="c1", state=state)
    assert ok["csv_id"] == "c1"
    assert ok["rows"] == 2
    assert ok["columns"] == ["a", "b"]

    nf = describe_csv.func(csv_id="missing", state=state)
    assert nf["csv_id"] == "missing"
    assert nf["rows"] is None
    assert nf["columns"] is None
    assert "not found" in nf["error"].lower()

    # sample_rows: not found returns structured error
    nf2 = sample_rows.func(csv_id="missing", state=state, n=5)
    assert nf2["csv_id"] == "missing"
    assert nf2["rows"] == []
    assert "not found" in nf2["error"].lower()

    # clamps n to [0,50] and returns list of rows
    many = CSVFile(
        id="many",
        columns=["x"],
        rows=[{"x": i} for i in range(60)],
        label=None,
    )
    state2 = {"csv_data": [many]}
    assert sample_rows.func(csv_id="many", state=state2, n=-1) == []
    assert len(sample_rows.func(csv_id="many", state=state2, n=100)) == 50
    assert sample_rows.func(csv_id="many", state=state2, n=2) == [{"x": 0}, {"x": 1}]


def test_upload_ack_suppresses_duplicate_ack_for_same_upload_id():
    c1 = CSVFile(id="csv_1", columns=["a"], rows=[{"a": 1}], label=None)
    out = upload_ack(
        {
            "mode": "upload",
            "messages": [HumanMessage(content="upload"), AIMessage(content="Uploaded csv_1")],
            "csv_data": [c1],
            "datasets": [],
            "last_uploaded_csv_id": "csv_1",
            "last_user_prompt": "upload",
        }
    )
    assert out["mode"] is None
    assert "messages" not in out


def test_chatbot_prefers_last_human_message_for_last_user_prompt():
    llm = _CapturingLLM()
    chatbot = make_chatbot_node(llm)

    out = chatbot(
        {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="prev"), HumanMessage(content="New ask")],
            "csv_data": [],
            "datasets": [],
            "last_user_prompt": "stale",
        }
    )

    assert out["last_user_prompt"] == "New ask"
    assert llm.last_messages is not None
    assert isinstance(llm.last_messages[-1], HumanMessage)
    assert llm.last_messages[-1].content == "New ask"
