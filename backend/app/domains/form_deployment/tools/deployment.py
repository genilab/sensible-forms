"""
File Deployment Middleware / Tools.

Responsible for:
- Performing form deployment functionality
"""

from __future__ import annotations

import io
import pandas as pd
import numpy as np

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


# Attempt to decode questions by type
def decode_question_type(row: pd.Series) -> dict:
    """Attempt to decode question data into types with required parameters."""
    question = {}
    question_type = row["question_type"]
    if question_type == "choiceQuestion": # A respondent can choose from a pre-defined set of options.
        # Collect options from row["response_options"]
        options = [{"value": opt} for opt in [item.strip() for item in row.get("response_options", "").split(";")]]
        if row.get("choice_type") in ["RADIO", "CHECKBOX"] and row["is_other"]:
            options.append({"isOther": True})
        return {
            "type": row.get("choice_type", "RADIO"), # RADIO, CHECKBOX, DROP_DOWN
            "options": options,
            "shuffle": False,
        }

    elif question_type == "dateQuestion": # A respondent can enter a date.
        return {
            "includeTime": False,
            "includeYear": True,
        }

    elif question_type == "scaleQuestion": # A respondent can choose a number from a range.
        # Convert NaN labels to None
        high_label = None if pd.isna(row["scale_max_label"]) else row["scale_max_label"]
        low_label = None if pd.isna(row["scale_min_label"]) else row["scale_min_label"]
        return {
            "high": row.get("scale_max", 5),
            "highLabel": high_label,
            "low": row.get("scale_min", 1),
            "lowLabel": low_label,
        }

    elif question_type == "textQuestion": # A respondent can enter a free text response.
        return {
            "paragraph": True,
        }

    elif question_type == "timeQuestion": # A respondent can enter a time.
        return {
            "duration": False,
        }

    else:
        raise ValueError(f"Question type unknown for row: {row}")


# Generate JSON-like dict for an input question specified in a CSV row
def format_question(index, row) -> dict:
    """Add question data to a formatted question dictionary for form batchUpdate."""
    if row["question_type"] in ["choiceQuestion", "dateQuestion", "scaleQuestion", "textQuestion", "timeQuestion"]:
        return {
            "requests": [
                {
                    "createItem": {
                        "item": {
                            "title": row.get("question_text", ""),
                            "questionItem": {
                                "question": {
                                    "required": row.get("required", False),
                                    row["question_type"]: decode_question_type(row),
                                }
                            },
                        },
                        "location": {"index": index},
                    }
                }
            ]
        }
    else:
        # Extension support for sections / grid questions should go here
        raise ValueError(f"Question type unknown for row: {row}")


# Deploy a Form Using Google Forms API
def form_deployment_deploy_form_tool(
    filename: str,
    file_bytes: bytes,
    creds: Credentials | None = None,
    *,
    encoding: str = "utf-8",
) -> dict:
    """Decode incoming CSV data and deploy the completed form. 
    Returns the form response dictionary."""
    if not file_bytes:
        raise ValueError("Uploaded CSV is empty. Add a header row and at least one question.")
    if not creds:
        raise ValueError("No credentials provided.")

    # Get CSV data
    text = file_bytes.decode(encoding, errors="replace")
    data = pd.read_csv(io.StringIO(text))

    # Make sure indexes pair with number of rows
    data = data.reset_index().infer_objects()
    
    # Clean dytpes
    data["choice_type"] = data["choice_type"].replace(np.nan, "RADIO").astype("str")
    data["is_other"] = data["is_other"].replace(np.nan, False).astype("bool")
    data["scale_min"] = pd.to_numeric(data["scale_min"], errors="coerce")
    data["scale_max"] = pd.to_numeric(data["scale_max"], errors="coerce")
    data["required"] = data["required"].replace(np.nan, False).astype("bool")
    
    # Format questions as list of JSON-like dicts
    questions = [format_question(index, row) for index, row in data.iterrows()]

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

        # Set publish settings
        set_publish_settings_request = {
            "publishSettings": {
                "publishState": {
                    "isPublished": True,
                    "isAcceptingResponses": True
                }
            },
        }
        publish_setting = (
            form_service
            .forms()
            .setPublishSettings(formId=result["formId"], body=set_publish_settings_request)
            .execute()
        )
        
        # Get response to show the questions have been added
        response = form_service.forms().get(formId=result["formId"]).execute()
        return response
