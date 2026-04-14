import os

# Keep tests deterministic even when developers have real API keys in their environment.
os.environ.setdefault("LLM_PROVIDER", "mock")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_question_generation_flow():
    r = client.post("/question-generation/", json={"topic": "Employee engagement"})
    assert r.status_code == 200
    body = r.json()
    assert "questions" in body
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) >= 1


def test_analysis_chat_flow_without_upload():
    r = client.post(
        "/analysis/chat",
        json={
            "message": "N=42. Overall satisfaction is 3.8/5.",
            "upload_mode": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert isinstance(body["message"], str)
    assert len(body["message"]) > 0


def test_upload_flow_rejects_non_csv():
    files = {"file": ("not.csv.txt", b"abc", "text/plain")}
    r = client.post("/analysis/uploads/", files=files)
    assert r.status_code == 400


def test_upload_flow_accepts_csv():
    files = {"file": ("sample.csv", b"a,b\n1,2\n", "text/csv")}
    r = client.post("/analysis/uploads/", files=files)
    assert r.status_code == 200
    assert r.json()["filename"] == "sample.csv"
    assert "file_id" in r.json()
    assert isinstance(r.json()["file_id"], str)


def test_analysis_chat_flow_with_upload_mode():
    files = {
        "file": (
            "responses.csv",
            b"responseId,lastSubmittedTime,Q1\nabc,2026-04-10T00:00:00Z,Yes\n",
            "text/csv",
        )
    }
    up = client.post("/analysis/uploads/", files=files)
    assert up.status_code == 200
    file_id = up.json()["file_id"]

    r = client.post(
        "/analysis/chat",
        json={
            "message": "",
            "upload_mode": True,
            "file_id": file_id,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "message" in body
    assert isinstance(body["message"], str)
    assert len(body["message"]) > 0


def test_analysis_chat_flow_followup_message():
    files = {"file": ("responses.csv", b"Q1\nYes\nNo\n", "text/csv")}
    up = client.post("/analysis/uploads/", files=files)
    file_id = up.json()["file_id"]

    first = client.post(
        "/analysis/chat",
        json={"message": "", "upload_mode": True, "file_id": file_id},
    ).json()

    follow = client.post(
        "/analysis/chat",
        json={
            "session_id": first["session_id"],
            "message": "What should I analyze next?",
            "upload_mode": False,
            "file_id": file_id,
        },
    )
    assert follow.status_code == 200
    body = follow.json()
    assert body["session_id"] == first["session_id"]
    assert isinstance(body["message"], str)
    assert len(body["message"]) > 0
