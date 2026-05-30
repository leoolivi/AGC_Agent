"""PendingConfirmation domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PendingConfirmation(BaseModel):
    id: UUID
    task_id: UUID
    user_id: UUID
    description: str
    data_for_review: dict
    risk_level: str
    status: str = "pending"
    user_comment: str | None = None
    group_id: UUID | None = None
    group_type: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
