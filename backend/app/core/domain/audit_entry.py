"""AuditEntry domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: UUID
    user_id: UUID | None = None
    session_id: str | None = None
    action_type: str
    tool_name: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    risk_score: int | None = None
    status: str | None = None
    llm_model: str | None = None
    created_at: datetime
