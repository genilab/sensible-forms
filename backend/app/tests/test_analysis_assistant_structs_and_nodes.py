from __future__ import annotations

from langgraph.graph import END
from langchain_core.messages import AIMessage

from app.domains.analysis_assistant.nodes.csv_loader import csv_loader
from app.domains.analysis_assistant.nodes.routing import (
    route,
    route_after_chatbot,
    route_after_ingestion,
    route_after_tool_node,
)
from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.utils.survey_helpers import (
    extract_long_response_value,
    known_question_ids,
    resolve_question_text,
)


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


def test_extract_long_response_value_prefers_standard_fields():
    assert extract_long_response_value({"answer": "x"}) == ("answer", "x")
    assert extract_long_response_value({"value": 10}) == ("value", 10)
    assert extract_long_response_value({"response": "y", "answer": "x"}) == ("response", "y")
    assert extract_long_response_value({"other": "z"}) == (None, None)


def test_csv_loader_adds_csvfile_and_sets_upload_mode(monkeypatch):
    # Make the id deterministic
    class _UUID:
        def __init__(self, s: str):
            self._s = s

        def __str__(self) -> str:
            return self._s

    import uuid as _uuid

    monkeypatch.setattr(_uuid, "uuid4", lambda: _UUID("fixed"))

    state = {"csv_text": "a,b\n1,2\n3,4\n", "csv_data": []}
    out = csv_loader(state)

    assert out["mode"] == "upload"
    assert out["csv_text"] is None
    assert out["last_uploaded_csv_id"] == "csv_fixed"
    assert len(out["csv_data"]) == 1
    assert out["csv_data"][0].columns == ["a", "b"]
    assert out["csv_data"][0].num_rows == 2


def test_routing_functions():
    assert route({"csv_text": "a,b\n1,2\n"}) == "csv_loader"
    assert route({"csv_text": None}) == "chatbot"

    # Upload mode always ends after chatbot
    st_upload = {"messages": [AIMessage(content="hi")], "mode": "upload"}
    assert route_after_chatbot(st_upload) == END

    # Tool calls => tool_node
    msg_with_tool = AIMessage(content="hi", tool_calls=[{"name": "x", "args": {}, "id": "t1", "type": "tool_call"}])
    st_tool = {"messages": [msg_with_tool], "mode": None}
    assert route_after_chatbot(st_tool) == "tool_node"

    # No tools => END
    st_no_tools = {"messages": [AIMessage(content="hi")], "mode": None}
    assert route_after_chatbot(st_no_tools) == END

    # After ingestion: upload => upload_ack
    st_ing_upload = {"messages": [AIMessage(content="done")], "mode": "upload"}
    assert route_after_ingestion(st_ing_upload) == "upload_ack"

    # After ingestion: tool call => tool_node
    st_ing_tool = {"messages": [msg_with_tool], "mode": "upload"}
    assert route_after_ingestion(st_ing_tool) == "tool_node"

    # After tool node: upload => upload_ack
    assert route_after_tool_node({"mode": "upload"}) == "upload_ack"
    assert route_after_tool_node({"mode": None}) == "chatbot"
