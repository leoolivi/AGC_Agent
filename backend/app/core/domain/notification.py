"""Notification domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Notification(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str | None = None
    level: str
    related_type: str | None = None
    related_id: UUID | None = None
    read: bool = False
    created_at: datetime
