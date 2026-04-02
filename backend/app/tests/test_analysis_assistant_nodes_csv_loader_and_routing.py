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
