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


def test_analysis_flow():
    r = client.post("/analysis/", json={"data_summary": "N=42. Overall satisfaction is 3.8/5."})
    assert r.status_code == 200
    body = r.json()
    assert "insights" in body
    assert isinstance(body["insights"], str)
    assert len(body["insights"]) > 0


def test_upload_flow_rejects_non_csv():
    files = {"file": ("not.csv.txt", b"abc", "text/plain")}
    r = client.post("/uploads/", files=files)
    assert r.status_code == 400


def test_upload_flow_accepts_csv():
    files = {"file": ("sample.csv", b"a,b\n1,2\n", "text/csv")}
    r = client.post("/uploads/", files=files)
    assert r.status_code == 200
    assert r.json()["filename"] == "sample.csv"
