'''
Unit tests for the Question Generation subsystem.
This tests:
- General chat functionality
- Checking if a response has a CSV code block
- Checking if a response does not have a CSV code block

This code was developed with assistance from Microsoft Copilot.
'''


from fastapi.testclient import TestClient
from app.main import app
import os

# Keep tests deterministic even when developers have real API keys in their environment.
#   Avoids inflating LLM costs unnecessarily
os.environ.setdefault("LLM_PROVIDER", "mock")

client = TestClient(app)


# Testing a general Question Generation chat
def test_question_generation_flow_chat():
    r = client.post("/question-generation/", json={"topic": "Employee engagement"})
    
    assert r.status_code == 200
    body = r.json()

    assert "questions" in body
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) >= 1

# Checking for a CSV code block
def test_question_generation_flow_csv_code_block():
    r = client.post("/question-generation/", json={"topic": "Provide me the following question in CSV format: 'What color is the sky?' Options: Blue, Green, Purple, or Orange."
        "No other information is needed in the CSV. Include commentary."})
    
    assert r.status_code == 200
    body = r.json()
    
    assert "questions" in body
    assert isinstance(body["questions"], list)
    questions = body["questions"]
    
    # Checking that there is a CSV code block somewhere in the response
    assert any("```csv" in q for q in questions)

# Testing to recognize a missing CSV code block
def test_question_generation_flow_missing_csv_code_block():
    r = client.post("/question-generation/", json={"topic": "Provide me the following question in CSV format without a code block: "
        "'What color is the sky?' Options: Blue, Green, Purple, or Orange."})
    
    assert r.status_code == 200
    body = r.json()

    assert "questions" in body
    assert isinstance(body["questions"], list)
    questions = body["questions"]

    # Checking that there is no CSV code block
    assert not any("```csv" in q for q in questions)