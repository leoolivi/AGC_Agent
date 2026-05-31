"""Google OAuth2 endpoints — authorize, callback, status, revoke."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.adapters.google import GoogleTokenStore
from app.api.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/oauth/google", tags=["oauth"])

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
]

# In-memory state store (production: use Redis or DB)
_pending_states: dict[str, str] = {}


def _build_flow() -> Flow:
    from pathlib import Path
    creds_file = Path(settings.google_credentials_file)
    if creds_file.exists():
        return Flow.from_client_secrets_file(
            str(creds_file), scopes=SCOPES, redirect_uri=settings.google_redirect_uri
        )
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


@router.post("/authorize")
async def authorize(user: dict = Depends(get_current_user)) -> dict:
    """Generate Google OAuth2 authorization URL."""
    from pathlib import Path
    if not settings.google_client_id and not Path(settings.google_credentials_file).exists():
        raise HTTPException(status_code=501, detail="Google integration not configured")

    flow = _build_flow()
    state = secrets.token_urlsafe(32)
    _pending_states[state] = user["sub"]

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return {"authorization_url": auth_url}


@router.get("/callback")
async def callback(code: str, state: str) -> RedirectResponse:
    """Handle Google OAuth2 callback — exchange code for tokens."""
    user_id = _pending_states.pop(state, None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    flow = _build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    if not credentials.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token received. Re-authorize with prompt=consent")

    store = GoogleTokenStore()
    await store.store_token(
        user_id=user_id,
        provider="google",
        refresh_token=credentials.refresh_token,
        scopes=list(credentials.scopes or SCOPES),
    )

    # Redirect to frontend settings page
    return RedirectResponse(url="http://localhost:5173/settings?google=connected")


@router.get("/status")
async def status(user: dict = Depends(get_current_user)) -> dict:
    """Check if user has valid Google OAuth token."""
    store = GoogleTokenStore()
    connected = await store.has_valid_token(user["sub"], "google")
    return {"connected": connected}


@router.post("/revoke")
async def revoke(user: dict = Depends(get_current_user)) -> dict:
    """Revoke Google OAuth token."""
    store = GoogleTokenStore()
    await store.revoke_token(user["sub"], "google")
    return {"status": "revoked"}
