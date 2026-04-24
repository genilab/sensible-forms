"""
OAuth2 API routes.

Responsible for:
- Handling OAuth2 requests

No domain logic should exist here.
"""

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from app.domains.form_deployment.tools import oauth
from app.infrastructure.config.settings import settings
import json

router = APIRouter(prefix="/auth", tags=["OAuth2"])

SCOPES = oauth.SCOPES
CLIENT_CONFIG = {"web": oauth.CLIENT_SECRETS}
REDIRECT_URI = oauth.REDIRECT_URI
FRONTEND_ROUTE = oauth.FRONTEND_ROUTE

COOKIE_NAME = "refresh_token"
COOKIE_SECURE = bool(settings.COOKIE_SECURE)
COOKIE_MAX_AGE = 30*24*60*60
COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"


@router.get("/start")
def auth_start():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        )
    
    code_verifier = getattr(flow, "code_verifier", None)
    state = getattr(getattr(flow, "oauth2session", None), "state", None)
    code_verifier = None if code_verifier is None else str(code_verifier)
    state = None if state is None else str(state)
    
    redirect = RedirectResponse(url=auth_url)
    redirect.set_cookie(
        key="oauth_flow",
        value=json.dumps({
            "state": state,
            "code_verifier": code_verifier,
        }),
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=300,
    )
    return redirect


@router.get("/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Missing auth callback code.")
    cookie = request.cookies.get("oauth_flow")
    if not cookie:
        raise HTTPException(400, "Missing OAuth cookie.")
    
    code_verifier = json.loads(cookie).get("code_verifier")
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials
    if not creds.refresh_token:
        raise HTTPException(400, "Missing refresh token.")
    
    # Query param "?oauth=complete" enables detecting popup flow completion
    redirect = RedirectResponse(url=f"{FRONTEND_ROUTE}?oauth=complete")
    redirect.delete_cookie("oauth_flow", path="/")
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=creds.refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=COOKIE_MAX_AGE,
    )
    return redirect


@router.post("/logout")
def logout(response: Response):
    try:
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, e)


@router.get("/status")
def status(request: Request):
    """Returns the current authentication status of the user."""
    refresh_token = request.cookies.get(COOKIE_NAME)
    return {"isAuth": bool(refresh_token and refresh_token != "null")}
