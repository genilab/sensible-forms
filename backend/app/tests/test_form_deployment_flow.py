import os
import csv

# Keep tests deterministic even when developers have real API keys in their environment.
os.environ.setdefault("LLM_PROVIDER", "mock")

from fastapi.testclient import TestClient
import asyncio
import pytest

from app.main import app


client = TestClient(app)
QUESTION_FILE_DIR = "backend/app/tests/question_files/"
TEST_FILE_DIR = "backend/app/tests/"
INVALID_QUESTION_FILES = [] # May be added as needed
with open(TEST_FILE_DIR+"formId_samples.csv") as file:
    formId_samples = list(csv.reader(file))[0]


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


# NOTE: The following tests require some setup to begin
#   1. Visit http://localhost:8000/auth/start in a browser and complete the consent flow
#   2. After redirect, copy the "refresh_token" value and paste into "REFRESH_TOKEN = ..." below
REFRESH_TOKEN = ...


def test_authentication():
    assert REFRESH_TOKEN, "Set REFRESH_TOKEN above this test"
    headers = {"cookie": f"refresh_token={REFRESH_TOKEN}"}
    r = client.get("/auth/status", headers=headers)
    assert r.status_code == 200
    assert r.json()["isAuth"], r.json()


# View at https://docs.google.com/forms/u/0/
def test_single_deployment():
    assert REFRESH_TOKEN, "Set REFRESH_TOKEN above this test"
    headers = {"cookie": f"refresh_token={REFRESH_TOKEN}"}
    file = os.listdir(QUESTION_FILE_DIR)[0]
    f = open(QUESTION_FILE_DIR+file, 'rb')
    files = {"file": (f.name, f, "text/csv")}
    r = client.post("/form-deployment/deploy", files=files, headers=headers)
    assert r.json()["status"] == "success", str(r.json())


# View at https://docs.google.com/forms/u/0/
# CAUTION: SLOW (~400s / ~6:40)
# NOTE: This test overwrites formId_sample.csv with new Form ID values
@pytest.mark.asyncio
async def test_all_deployments():
    assert REFRESH_TOKEN, "Set REFRESH_TOKEN above this test"
    headers = {"cookie": f"refresh_token={REFRESH_TOKEN}"}
    formId_samples = []
    for file in os.listdir(QUESTION_FILE_DIR):
        f = open(QUESTION_FILE_DIR+file, 'rb')
        files = {"file": (f.name, f, "text/csv")}
        r = client.post("/form-deployment/deploy", files=files, headers=headers)
        if file in INVALID_QUESTION_FILES:
            assert r.json()["status"] == "error"
        else: 
            assert r.json()["status"] == "success", f.name+"\n"+r.json()["feedback"]
            formId_samples.append(r.json()["formId"])
        await asyncio.sleep(10)
    with open(TEST_FILE_DIR+"formId_samples.csv", 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(formId_samples)


# NOTE: The following tests require some setup to begin
#  1. Visit https://docs.google.com/forms/u/0/
#  2. Provide at least 1 response for each form generated in the previous test


def test_single_retrieval():
    assert REFRESH_TOKEN, "Set REFRESH_TOKEN above this test"
    headers = {"cookie": f"refresh_token={REFRESH_TOKEN}"}
    formId = formId_samples[0]
    r = client.get("/form-deployment/retrieve", params={"formId": formId}, headers=headers)
    assert r.json()["status"] == "success", str(r.json())


def test_all_retrievals():
    assert REFRESH_TOKEN, "Set REFRESH_TOKEN above this test"
    headers = {"cookie": f"refresh_token={REFRESH_TOKEN}"}
    for formId in formId_samples:
        r = client.get("/form-deployment/retrieve", params={"formId": formId}, headers=headers)
        assert r.json()["status"] == "success", str(r.json())
