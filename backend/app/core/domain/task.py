"""AgentTask domain model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AgentTask(BaseModel):
    id: UUID
    user_id: UUID
    session_id: str | None = None
    action_type: str
    tool_name: str | None = None
    tool_args: dict = {}
    status: str = "pending"
    risk_score: int
    depends_on_task_id: UUID | None = None
    result: dict | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
