"""
File Deployment Middleware / Tools.

Responsible for:
- Performing form retrieval functionality
"""

from __future__ import annotations

import io
import csv

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


# Convert response and question Data to CSV
def convert_to_csv_str(responses: list, questions: dict) -> str:
    """Convert response and question Data to CSV as a str."""
    out_str = io.StringIO()
    writer = csv.writer(out_str, quoting=csv.QUOTE_MINIMAL)

    # Initialize out_str with columns / header row
    columns = ["responseId", "lastSubmittedTime"] + list(questions.values())
    writer.writerow(columns)

    # Append rows
    for response in responses: # Iterate through all responses
        row = [
            response.get("responseId"), # Add row responseId
            response.get("lastSubmittedTime") # Add row lastSubmittedTime
        ]

        answers = response.get("answers")
        for question_id in questions.keys(): # Iterate through all questions
            # Get the value and replace newline characters with a space
            answer_values = [
                answer.get('value', '')
                for answer in answers
                .get(question_id, {})
                .get('textAnswers', {})
                .get('answers', [])
            ]
            if answer_values:
                # Separate multiple answers with ';'
                row.append("; ".join(answer_values).replace('\n', ' '))
            else:
                # Add "No answer" if not found
                row.append("No answer")

        writer.writerow(row)
    return out_str.getvalue()


# Retrieve a Form Using Google Forms API
def form_deployment_retrieve_form_tool(
    formId: str,
    creds: Credentials | None = None,
    *,
    encoding: str = "utf-8",
) -> str:
    """Retrieve remote form data as a CSV file. 
    Returns a response dictionary containing the CSV content."""
    if not formId:
        raise ValueError("No Form ID detected. Enter a valid Form ID.")
    if not creds:
        raise ValueError("No credentials provided.")

    with build("forms", "v1", credentials=creds) as form_service: 
        # Get the responses of your specified form:
        resp_data = form_service.forms().responses().list(formId=formId).execute()
        responses = resp_data.get("responses")
        if responses is None:
            raise ValueError("No responses found.")

        # Get the questions of your specified form:
        form_data = form_service.forms().get(formId=formId).execute()
        questions = {
            item["questionItem"]["question"]["questionId"]: item.get("title", "")
            for item in form_data.get("items", []) if "questionItem" in item
        }
        
        # Convert the responses and questions to the str/dictionary format
        return convert_to_csv_str(responses, questions)
