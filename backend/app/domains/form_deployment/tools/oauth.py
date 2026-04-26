"""
File Deployment Middleware / Tools.

Responsible for:
- Validating user credentials
"""

from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# Get client secrets from backend root
def get_client_secrets() -> dict:
    """Use Render Secrets File storage to find client_secrets.json"""
    backend_dir = Path(__file__).resolve().parents[4] # .../backend
    secrets_path = backend_dir / "client_secrets.json"

    # Ensure client_secrets.json exists
    if not secrets_path.exists():
        raise RuntimeError("No API access route detected.")
    
    load = json.loads(secrets_path.read_text())
    return load.get("web") or load.get("installed")
    

# Set dependencies
CLIENT_SECRETS = get_client_secrets()
TOKEN_URI = CLIENT_SECRETS.get("token_uri", "https://oauth2.googleapis.com/token")
REDIRECT_URI = CLIENT_SECRETS.get("redirect_uris", ["http://localhost:8000/auth/callback"])[0]
FRONTEND_ROUTE = CLIENT_SECRETS.get("javascript_origins", ["http://localhost:5173"])[0]+"/"
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]


# Get user credentials
def get_credentials(
    refresh_token: str | None = None,
    scopes: list[str] = SCOPES,
    ) -> Credentials:
    """Use Google OAuth2 handlers to get user and client authentication."""
    # Attempt credential creation from refresh token and client secrets
    if refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=CLIENT_SECRETS["client_id"],
            client_secret=CLIENT_SECRETS["client_secret"],
            token_uri=TOKEN_URI,
            scopes=scopes,
        )
        creds.refresh(Request())
        return creds
    raise ValueError("No valid authentication tokens detected.")
