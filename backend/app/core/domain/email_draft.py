"""EmailDraft domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EmailDraft(BaseModel):
    id: UUID
    user_id: UUID
    task_id: UUID | None = None
    to_addresses: list[str]
    subject: str
    body_html: str
    body_text: str
    status: str = "pending_review"
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime
