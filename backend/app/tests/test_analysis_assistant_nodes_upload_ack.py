from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.domains.analysis_assistant.nodes.upload_ack import upload_ack
from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset


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
