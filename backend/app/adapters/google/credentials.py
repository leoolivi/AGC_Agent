"""Google credentials helper — provides valid Credentials for any adapter."""
from __future__ import annotations

import structlog
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.adapters.google import GoogleTokenStore
from app.config import settings

logger = structlog.get_logger()


class GoogleAuthExpiredError(Exception):
    """Raised when refresh token is revoked or expired."""
    pass


async def get_credentials(user_id: str) -> Credentials:
    """Get valid Google credentials for a user. Auto-refreshes access token."""
    store = GoogleTokenStore()
    refresh_token = await store.get_token(user_id, "google")

    if not refresh_token:
        raise GoogleAuthExpiredError("No Google token found. User must re-authorize.")

    # Load client_id/secret from JSON file or settings
    client_id = settings.google_client_id
    client_secret = settings.google_client_secret
    from pathlib import Path
    creds_file = Path(settings.google_credentials_file)
    if creds_file.exists():
        import json
        data = json.loads(creds_file.read_text())
        web = data.get("web", data.get("installed", {}))
        client_id = web.get("client_id", client_id)
        client_secret = web.get("client_secret", client_secret)

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    # Refresh to get a valid access token
    try:
        creds.refresh(Request())
    except RefreshError as e:
        # Token revoked or expired — mark as revoked
        await store.revoke_token(user_id, "google")
        logger.warning("google_token_refresh_failed", user_id=user_id, error=str(e))
        raise GoogleAuthExpiredError("Google token expired. User must re-authorize.") from e

    return creds
