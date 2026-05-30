"""Storage utilities shared across adapters."""
from __future__ import annotations

from datetime import datetime, timezone


def build_storage_key(user_id: str, file_id: str, filename: str) -> str:
    """Build storage key: {user_id}/{year}/{month}/{file_id}_{original_filename}."""
    now = datetime.now(timezone.utc)
    return f"{user_id}/{now.year}/{now.month:02d}/{file_id}_{filename}"
