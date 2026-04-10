import os

# Keep tests deterministic even when developers have real API keys in their environment.
os.environ.setdefault("LLM_PROVIDER", "mock")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# API: /health returns an OK status payload.
def test_healthcheck():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# API: question generation endpoint responds with a non-empty list.
def test_question_generation_flow():
    r = client.post("/question-generation/", json={"topic": "Employee engagement"})
    assert r.status_code == 200
    body = r.json()
    assert "questions" in body
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) >= 1


# API: analysis endpoint responds with a non-empty insights string.
def test_analysis_flow():
    r = client.post("/analysis/", json={"data_summary": "N=42. Overall satisfaction is 3.8/5."})
    assert r.status_code == 200
    body = r.json()
    assert "insights" in body
    assert isinstance(body["insights"], str)
    assert len(body["insights"]) > 0


<<<<<<< HEAD:backend/app/tests/test_api_smoke_flows.py
# API: analysis endpoint accepts a chat-style messages payload.
def test_analysis_flow_accepts_messages():
    r = client.post(
        "/analysis/",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Given this summary, provide 3 insights: N=42 satisfaction 3.8/5.",
                }
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "insights" in body
    assert isinstance(body["insights"], str)
    assert len(body["insights"]) > 0


# API: form deployment upload + chat workflow returns expected shapes.
def test_form_deployment_flow():
    files = {"file": ("survey.csv", b"question_text,question_type\nHello?,short_text\n", "text/csv")}
    deploy_r = client.post("/form-deployment/deploy", files=files)
    assert deploy_r.status_code == 200
    deploy_body = deploy_r.json()
    assert deploy_body["status"] in {"success", "error"}
    assert isinstance(deploy_body["feedback"], str)

    chat_r = client.post(
        "/form-deployment/chat",
        json={
            "message": "Did it deploy?",
            "last_deploy_filename": deploy_body["filename"],
            "last_deploy_status": deploy_body["status"],
            "last_deploy_feedback": deploy_body["feedback"],
        },
    )
    assert chat_r.status_code == 200
    chat_body = chat_r.json()
    assert "message" in chat_body
    assert isinstance(chat_body["message"], str)


# API: uploads endpoint rejects non-CSV uploads.
=======
>>>>>>> origin/main:backend/app/tests/test_example_flow.py
def test_upload_flow_rejects_non_csv():
    files = {"file": ("not.csv.txt", b"abc", "text/plain")}
    r = client.post("/uploads/", files=files)
    assert r.status_code == 400


# API: uploads endpoint accepts CSV uploads and returns the filename.
def test_upload_flow_accepts_csv():
    files = {"file": ("sample.csv", b"a,b\n1,2\n", "text/csv")}
    r = client.post("/uploads/", files=files)
    assert r.status_code == 200
    assert r.json()["filename"] == "sample.csv"


# API: analysis/upload ingests CSVs and persists session state across repeated uploads.
def test_analysis_upload_ingests_csv_and_persists_session_state():
    # First upload seeds the session with a single CSV.
    session_id = "00000000-0000-0000-0000-000000000001"
    files = {"file": ("one.csv", b"a,b\n1,2\n", "text/csv")}
    data = {"session_id": session_id}
    r1 = client.post("/analysis/upload", files=files, data=data)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["session_id"] == session_id
    assert "Thanks" in body1["insights"]

    # Second upload in the same session should see prior state.
    files2 = {"file": ("two.csv", b"a,b\n3,4\n", "text/csv")}
    r2 = client.post("/analysis/upload", files=files2, data=data)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["session_id"] == session_id
    assert "I now have access to 2 CSV files" in body2["insights"]
