from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analysis_upload_rejects_non_csv_file_extension():
    files = {"file": ("not.csv.txt", b"abc", "text/plain")}
    r = client.post("/analysis/upload", files=files)
    assert r.status_code == 400
    assert r.json()["detail"] == "Only .csv files are allowed."


def test_analysis_upload_rejects_invalid_session_id():
    files = {"file": ("one.csv", b"a,b\n1,2\n", "text/csv")}
    data = {"session_id": "not-a-uuid"}
    r = client.post("/analysis/upload", files=files, data=data)
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid session_id (expected UUID)."


def test_analysis_upload_accepts_missing_session_id_and_generates_one():
    files = {"file": ("one.csv", b"a,b\n1,2\n", "text/csv")}
    r = client.post("/analysis/upload", files=files)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("insights"), str)
    assert body["insights"]
    # Should always return a valid UUID session_id.
    UUID(body["session_id"])


def test_analysis_upload_acknowledges_even_with_prior_chat_ai_message():
    # Seed the checkpoint thread with a prior chatbot response (non-upload).
    # This mimics the real flow: user chats first, then uploads a CSV.
    session_id = "11111111-1111-1111-1111-111111111111"
    r1 = client.post(
        "/analysis/",
        json={"data_summary": "N=1", "session_id": session_id},
    )
    assert r1.status_code == 200

    files = {"file": ("one.csv", b"a,b\n1,2\n", "text/csv")}
    r2 = client.post(
        "/analysis/upload",
        files=files,
        data={"session_id": session_id},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert isinstance(body.get("insights"), str)
    # The upload branch should produce a deterministic acknowledgement.
    assert "uploaded" in body["insights"].lower()
