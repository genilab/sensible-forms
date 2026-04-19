"""
File Deployment Middleware / Tools.

Responsible for:
- Validating user credentials
"""

from __future__ import annotations

import os
from pathlib import Path

import google.auth.external_account_authorized_user as ext
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


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
    backend_dir = this_file.parents[4]  # .../backend
    CLIENT_SECRETS_PATH = backend_dir / "client_secrets.json"
    TOKEN_JSON_PATH = backend_dir / "token.json"

    # Ensure client_secrets.json exists
    if not os.path.exists(CLIENT_SECRETS_PATH): 
        raise ValueError("No API access route detected.")

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
