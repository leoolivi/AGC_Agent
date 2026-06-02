"""OAuth scope validation helpers for source and calendar APIs."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.adapters.google import GoogleTokenStore

SOURCE_REQUIRED_SCOPES: dict[str, str] = {
    "drive": "https://www.googleapis.com/auth/drive.readonly",
    "gmail": "https://www.googleapis.com/auth/gmail.readonly",
    "calendar": "https://www.googleapis.com/auth/calendar.events",
}


async def validate_source_oauth_scope(user_id: str, source_type: str) -> None:
    """Raise 403 if user lacks OAuth scope for the source type."""
    required = SOURCE_REQUIRED_SCOPES.get(source_type)
    if not required:
        raise HTTPException(status_code=400, detail=f"Unknown source type: {source_type}")

    store = GoogleTokenStore()
    has_token = await store.has_valid_token(user_id, "google", required)
    if not has_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "insufficient_oauth_scopes",
                "missing_scopes": [required],
                "source_type": source_type,
            },
        )


async def check_oauth_scopes(user_id: str, source_type: str) -> dict:
    """Return scope status without raising."""
    required = SOURCE_REQUIRED_SCOPES.get(source_type, "")
    store = GoogleTokenStore()
    sufficient = await store.has_valid_token(user_id, "google", required) if required else False
    return {
        "source_type": source_type,
        "required_scope": required,
        "sufficient": sufficient,
        "missing_scopes": [] if sufficient else ([required] if required else []),
    }
