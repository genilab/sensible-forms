import os

# Keep tests deterministic even when developers have real API keys in their environment.
os.environ.setdefault("LLM_PROVIDER", "mock")

from fastapi.testclient import TestClient
import asyncio
import pytest

from app.main import app


client = TestClient(app)
QUESTION_FILE_DIR = "backend/app/tests/question_files/"
INVALID_QUESTION_FILES = [
    "questions_11.csv",
    "questions_12.csv",
    "questions_13.csv",
    "questions_15.csv",
    "questions_2.csv",
    "questions_21.csv",
    "questions_22.csv",
    "questions_23.csv",
    "questions_4.csv",
    "questions_7.csv",
]
FORMID_SAMPLES = [
    "11jGGCenhoY2yRIRJ2sJ5N-GHb4ExnvTw1J7YfYhXuWg",
    "1dpYows5TouZB_AZQru7rc4Ko-l09H5cPvsmLTf92O4A",
    "17wd6QqdvIIBEmFZSiM8n2xSOcWHEIPDVOd9fMCAEx2k",
    "1hn4hsEaj4FXeTVRKipmQmp8mVJjjuERRSrXXJ7CdukU",
    "1SePoym4o26kSK2OZHFhfeqX4AzyIxvmBmOPkXMJf0Eo",
    "1px4kmsuxe5oHJbkLJr4ABcamurKIdoxOXQBBVx_jZGA",
    "1tAeswUF12tsJKNrt5jAhsSot1GR93hRDiYaCK3-wV64",
    "1X8Hq1YEWRZgrCov6Jf2Obmp9G2oHSkXajIPAum3yOR0",
    "13yDYU5Y4XZcn86-y3AzjNQ86Cgz1SDp9_RsEzxxYFFo",
    "1GjCR6UqwZmyrfQmp6_XR58SlhyYAjsyepMkQIMaHkdQ",
    "1qY0OU44O9-6BtMFOuao5q1JPC53vgZnt-l2iNVVW6QA",
    "1t-oQNiUeBu4gGIdqnKtVITfoJJN-FsN3rGKulHixBWg",
    "1b2mc9EbRxVvvmk9lUHbQBHqIWbrn2-oa1LJZxO-fwgY",
    "1m0HkYFl9LeyCaPz5VwgPgouoQbg2SahugljLQ66nMq4",
    "1DsMi4OH8cKW-zZblh7INYjb0IV37r2LMCvZHmuZRago",
]


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


def test_all_sample_question_files():
    for file in os.listdir(QUESTION_FILE_DIR):
        f = open(QUESTION_FILE_DIR+file, 'rb')
        files = {"file": (f.name, f, "text/csv")}
        r = client.post("/uploads/", files=files)
        assert r.status_code == 200
        assert r.json()["filename"] == f.name


# View at https://docs.google.com/forms/u/0/
def test_single_deployment():
    file = os.listdir(QUESTION_FILE_DIR)[0]
    f = open(QUESTION_FILE_DIR+file, 'rb')
    files = {"file": (f.name, f, "text/csv")}
    r = client.post("/form-deployment/deploy", files=files)
    assert r.json()["status"] == "success"


# View at https://docs.google.com/forms/u/0/
# CAUTION: SLOW (~320s / ~5:20)
@pytest.mark.asyncio
async def test_all_deployments():
    for file in os.listdir(QUESTION_FILE_DIR):
        f = open(QUESTION_FILE_DIR+file, 'rb')
        files = {"file": (f.name, f, "text/csv")}
        r = client.post("/form-deployment/deploy", files=files)
        if file in INVALID_QUESTION_FILES:
            assert r.json()["status"] == "error"
        else: 
            assert r.json()["status"] == "success", f.name+"\n"+r.json()["feedback"]
        await asyncio.sleep(10)


def test_single_retrieval():
    formId = FORMID_SAMPLES[0]
    r = client.get("/form-deployment/retrieve", params={"formId": formId})
    assert r.json()["status"] == "success", str(r.json())


def test_all_retrievals():
    for formId in FORMID_SAMPLES:
        r = client.get("/form-deployment/retrieve", params={"formId": formId})
        assert r.json()["status"] == "success", str(r.json())
