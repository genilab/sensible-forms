from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domains.analysis_assistant.nodes.chatbot import make_chatbot_node
from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset


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
