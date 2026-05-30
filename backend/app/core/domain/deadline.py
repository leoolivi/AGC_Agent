"""Deadline domain model."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class Deadline(BaseModel):
    id: UUID
    user_id: UUID
    document_id: UUID | None = None
    title: str
    description: str | None = None
    due_date: date
    deadline_type: str = "custom"
    recurrence: str = "none"
    recurrence_config: dict = {}
    status: str = "active"
    source: str = "manual"
    source_confidence: float | None = None
    source_text: str | None = None
    notified_at: list[dict] = []
    created_at: datetime
