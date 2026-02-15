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


def test_upload_flow_rejects_non_csv():
    files = {"file": ("not.csv.txt", b"abc", "text/plain")}
    r = client.post("/uploads/", files=files)
    assert r.status_code == 400


def test_upload_flow_accepts_csv():
    files = {"file": ("sample.csv", b"a,b\n1,2\n", "text/csv")}
    r = client.post("/uploads/", files=files)
    assert r.status_code == 200
    assert r.json()["filename"] == "sample.csv"
