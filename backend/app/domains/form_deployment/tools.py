"""
File Deployment Middleware / Tools.

Responsible for:
- Validating uploaded file parameters
- Performing form deployment functionality

"""

from __future__ import annotations

import io
import csv
import pandas as pd
import numpy as np
from pathlib import Path

import os
import google.auth.external_account_authorized_user as ext
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Form Deployment CSV check tool definition @tool
def form_deployment_check_csv_tool(
    file_bytes: bytes,
    *,
    encoding: str = "utf-8",
) -> None:
    """Checks if a CSV file format is correct after the user enters 'Check File'."""
    if not file_bytes:
        raise ValueError("Uploaded CSV is empty. Add a header row and at least one question.")

    text = file_bytes.decode(encoding, errors="replace")
    data = pd.read_csv(io.StringIO(text))
    errors = []

    # 1. Confirm data is in state - critical
    if data.empty:
        errors.append("\nNo CSV file uploaded.\n")

    else:
        df = data.replace('', np.nan).infer_objects() # Normalize empty strings to np.nan for consistent handling and fix FutureWarning

        # 2. Confirm columns exist in dataframe - critical
        columns = df.columns.tolist() if not df.empty else [] # Handle empty DataFrame
        if not columns:
            errors.append("\nNo columns detected in CSV.\n")

        # 3. Check column names - critical
        valid_columns = ["question_id", "question_text", "question_type", "response_options", "scale_min", "scale_max", "scale_min_label", "scale_max_label", "required"]
        if columns != valid_columns:
            invalid_columns = [col for col in columns if col not in valid_columns]
            errors.append(f"""
            CSV columns are incorrect.
            The correct columns are: {", ".join(valid_columns)}
            The current invalid columns are: {", ".join(invalid_columns)}
            """)

        # Only proceed with further checks if critical errors have not occurred
        if not errors:

            # 4. Check for valid question types
            valid_types = ["choiceQuestion", "textQuestion", "scaleQuestion", "dateQuestion", "timeQuestion"]
            if not df["question_type"].isin(valid_types).all():
                invalid_rows = df[~df["question_type"].isin(valid_types)].index.tolist()
                invalid_types = df.loc[invalid_rows, 'question_type'].tolist()
                errors.append(f"""
                Invalid question types detected.
                The correct question types are: {", ".join(valid_types)}
                The current invalid rows are: {", ".join(map(str, invalid_rows))}
                The current invalid question types are: {", ".join(map(str, invalid_types))}
                """)

            # 5. Check for ;-separated response_options (ignoring NaN/empty entries)
            if df['response_options'].notna().any() and not df['response_options'].dropna().apply(lambda x: ';' in str(x)).all():
                invalid_rows = df[df['response_options'].notna() & ~df['response_options'].apply(lambda x: ';' in str(x))].index.tolist()
                invalid_responses = df.loc[invalid_rows, 'response_options'].tolist()
                errors.append(f"""
                Response options are incorrectly formatted.
                Valid response options must be separated by semicolons if provided.
                The current invalid rows are: {", ".join(map(str, invalid_rows))}
                The current invalid response options are: {", ".join(map(str, invalid_responses))}
                """)

            # 6. Check for int/float in scale_min & scale_max
            # Check if 'scale_min' can be converted to numeric (ignoring NaN)
            numeric_scale_min = pd.to_numeric(df['scale_min'], errors='coerce')
            invalid_scale_min_rows = df[numeric_scale_min.isna() & df['scale_min'].notna()]
            if not invalid_scale_min_rows.empty:
                invalid_rows_idx = invalid_scale_min_rows.index.tolist()
                invalid_values = invalid_scale_min_rows['scale_min'].tolist()
                errors.append(f"""
                Invalid scale options detected in 'scale_min'.
                Valid scale options must be numbers.
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'scale_min' values are: {", ".join(map(str, invalid_values))}
                """)

            # Check if 'scale_max' can be converted to numeric (ignoring NaN)
            numeric_scale_max = pd.to_numeric(df['scale_max'], errors='coerce')
            invalid_scale_max_rows = df[numeric_scale_max.isna() & df['scale_max'].notna()]
            if not invalid_scale_max_rows.empty:
                invalid_rows_idx = invalid_scale_max_rows.index.tolist()
                invalid_values = invalid_scale_max_rows['scale_max'].tolist()
                errors.append(f"""
                Invalid scale options detected in 'scale_max'.
                Valid scale options must be numbers.
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'scale_max' values are: {", ".join(map(str, invalid_values))}
                """)

            # 7. Check for bool in 'required'
            valid_bool_values = ['true', 'false', '1', '0', '1.0', '0.0']
            invalid_required_rows = df[df['required'].notna() & ~df['required'].astype(str).str.lower().isin(valid_bool_values)]
            if not invalid_required_rows.empty:
                invalid_rows_idx = invalid_required_rows.index.tolist()
                invalid_values = invalid_required_rows['required'].tolist()
                errors.append(f"""
                Invalid values detected in 'required' column.
                Valid values must be boolean (True/False) or interpretable as such (e.g. {", ".join(valid_bool_values)}).
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'required' values are: {", ".join(map(str, invalid_values))}
                """)

            # 8. Check for empty rows
            empty_rows = df[df.isnull().all(axis=1)]
            if not empty_rows.empty:
                empty_rows_idx = empty_rows.index.tolist()
                errors.append(f"""
                Empty rows detected at indices: {', '.join(map(str, empty_rows_idx))}
                """)

    if errors:
        raise ValueError("".join(errors))


# Attempt to decode questions by type
def decode_question_type(row: pd.Series) -> dict:
    """Attempt to decode question data into types with required parameters."""
    question = {}
    question_type = row["question_type"]
    if question_type == "choiceQuestion": # A respondent can choose from a pre-defined set of options.
        # Collect options from row["response_options"]
        options = [{"value": opt} for opt in [item.strip() for item in row["response_options"].split(";")]]
        question = {
            "type": "RADIO", # Options as buttons
            "options": options,
            "shuffle": False,
        }

    elif question_type == "dateQuestion": # A respondent can enter a date.
        question = {
            "includeTime": False,
            "includeYear": True,
        }

    elif question_type == "scaleQuestion": # A respondent can choose a number from a range.
        # Convert NaN labels to None
        high_label = None if pd.isna(row["scale_max_label"]) else row["scale_max_label"]
        low_label = None if pd.isna(row["scale_min_label"]) else row["scale_min_label"]
        question = {
            "high": row["scale_max"],
            "highLabel": high_label,
            "low": row["scale_min"],
            "lowLabel": low_label,
        }

    elif question_type == "textQuestion": # A respondent can enter a free text response.
        question = {
            "paragraph": True,
        }

    elif question_type == "timeQuestion": # A respondent can enter a time.
        question = {
            "duration": False,
        }

    else:
        raise ValueError(f"Question type unknown for row: {row}")
    return question


# Generate JSON-like dict for an input question specified in a CSV row
def format_question(index, row) -> dict:
    """Add question data to a formatted question dictionary for form batchUpdate."""
    NEW_QUESTION = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": (row["question_text"]),
                        "questionItem": {
                            "question": {
                                "required": row["required"],
                                row["question_type"]: decode_question_type(row),
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        ]
    }
    return NEW_QUESTION


# Get user credentials
def get_credentials(
    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.responses.readonly",
        ],
    ) -> Credentials | ext.Credentials:
    """Use Google OAuth2 handlers to get user and client authentication."""
    # Set defaults
    credentials = None
    this_file = Path(__file__).resolve()
    backend_dir = this_file.parents[3]  # .../backend
    CLIENT_SECRETS_PATH = backend_dir / "client_secrets.json"
    TOKEN_JSON_PATH = backend_dir / "token.json"

    # 1. Load credentials from file if they exist, and refresh if needed
    if os.path.exists(TOKEN_JSON_PATH):
        with open(TOKEN_JSON_PATH, 'rb') as token:
            credentials = Credentials.from_authorized_user_file(
                TOKEN_JSON_PATH,
                SCOPES,
            )

    # Refresh or re-authorize if credentials are invalid or missing
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            # 2. Refresh the token if expired
            try:
                credentials.refresh(Request())
                return credentials
            except:
                os.remove(TOKEN_JSON_PATH)

        # 3. Create a flow object and redirect the user to log in
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_PATH,
            SCOPES,
        )
        credentials = flow.run_local_server(prompt="consent")
        
        # 4. Save user credentials for future use
        with open(TOKEN_JSON_PATH, 'w') as token:
            token.write(credentials.to_json())

    return credentials


# Deploy a Form Using Google Forms API
def form_deployment_deploy_form_tool(
    filename: str,
    file_bytes: bytes,
    *,
    encoding: str = "utf-8",
) -> dict:
    """Decode incoming CSV data and deploy the completed form. 
    Returns the form response dictionary."""
    if not file_bytes:
        raise ValueError("Uploaded CSV is empty. Add a header row and at least one question.")

    # Get CSV data
    text = file_bytes.decode(encoding, errors="replace")
    data = pd.read_csv(io.StringIO(text))

    # Format questions as list of JSON-like dicts
    data = data.reset_index() # Make sure indexes pair with number of rows
    questions = [format_question(index, row) for index, row in data.iterrows()]

    # Get user credentials
    creds = get_credentials()
    with build("forms", "v1", credentials=creds) as form_service: 
        # Request body for creating a form
        NEW_FORM = {
            "info": {
                "documentTitle": filename[:-4], # Remove ".csv"
                "title": filename[:-4],
            }
        }

        # Create the initial form
        result = form_service.forms().create(body=NEW_FORM).execute()
        # Add questions to the form
        for NEW_QUESTION in questions:
            # Prepare question setting
            question_setting = (
                form_service.forms()
                .batchUpdate(formId=result["formId"], body=NEW_QUESTION)
                .execute()
            )

        # Return the response to show the questions have been added
        response = form_service.forms().get(formId=result["formId"]).execute()
        return response


# Convert response and question Data to CSV (now unused)
def convert_to_csv_dict(responses: list, questions: dict) -> dict[str, list]:
    """Convert response and question Data to CSV as a dict."""
    columns = ["responseId", "lastSubmittedTime"] + [question for question in questions.values()]
    
    # Initialize out_dict with a new empty list for each key
    out_dict = {key: [] for key in columns}

    for response in responses: # Iterate through all responses
        out_dict["responseId"].append(response.get("responseId")) # Add row responseId
        out_dict["lastSubmittedTime"].append(response.get("lastSubmittedTime")) # Add row lastSubmittedTime

        answers = response["answers"]
        for question_id in questions.keys(): # Iterate through all response questions
            try:
                # Get the value and replace newline characters with a space
                value = answers.get(question_id)["textAnswers"]["answers"][0]["value"]
                out_dict[questions[question_id]].append(value.replace('\n', ' ')) # Add answer, with newlines replaced
            except:
                out_dict[questions[question_id]].append("No answer") # Add "No answer", if not found

    return out_dict


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
            try:
                # Get the value and replace newline characters with a space
                row.append(
                    answers
                    .get(question_id, {})
                    .get("textAnswers", {})
                    .get("answers", [])[0]
                    .get("value", "")
                    .replace('\n', ' ')
                )
            except (KeyError, IndexError, TypeError):
                row.append("No answer") # Add "No answer" if not found
        
        writer.writerow(row)
    return out_str.getvalue()


# Deploy a Form Using Google Forms API
def form_deployment_retrieve_form_tool(
    formId: str,
    *,
    encoding: str = "utf-8",
    output_type: str = "str",
) -> str | dict:
    """Retrieve remote form data as a CSV file. 
    Returns a response dictionary containing the CSV content."""
    if not formId: 
        raise ValueError("No Form ID detected. Enter a valid Form ID.")

    # Get user credentials
    creds = get_credentials()
    with build("forms", "v1", credentials=creds) as form_service: 
        # Get the responses of your specified form:
        resp_data = form_service.forms().responses().list(formId=formId).execute()
        responses = resp_data.get("responses")

        # Get the questions of your specified form:
        form_data = form_service.forms().get(formId=formId).execute()
        questions = {
            item["questionItem"]["question"]["questionId"]: item.get("title", "")
            for item in form_data.get("items", []) if "questionItem" in item
        }
        
        # Convert the responses and questions to the str/dictionary format
        return convert_to_csv_str(responses, questions) \
            if output_type == "str" else convert_to_csv_dict(responses, questions)


# Optional testing scripts, may be removed safely
if __name__ == "__main__":
    import json
    test = None

    if test == 1:
        # Set test variables
        filename = "example_form.csv"
        with open("backend/app/tests/test_questions.csv", 'rb') as file:
            file_bytes = file.read()
        
        # Test deployment and print response JSON
        response = form_deployment_deploy_form_tool(filename, file_bytes)
        response_dump = json.dumps(response, sort_keys=True, indent=4)
        print(response_dump)
        print(f"Publisher link: https://docs.google.com/forms/d/{response["formId"]}/edit")
        print(f"Responder link: {response["responderUri"]}")
    
    elif test == 2:
        # Test retrieval and print response dict
        formId = "1OK5awRN_pk1qpU3gFA92t8lo_lJCSmVudaWo4UbaWk0"
        response = form_deployment_retrieve_form_tool(formId, output_type="dict")
        response_dump = json.dumps(response, sort_keys=True, indent=4)
        print(response_dump)

    elif test == 3:
        # Test retrieval and print response str
        formId = "1OK5awRN_pk1qpU3gFA92t8lo_lJCSmVudaWo4UbaWk0"
        response = form_deployment_retrieve_form_tool(formId)
        print(response)
