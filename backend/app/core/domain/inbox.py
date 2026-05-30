"""Agent Inbox domain models."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AgentInboxItem(BaseModel):
    id: UUID
    user_id: UUID
    event_type: str
    event_source: dict
    source_ref_id: UUID | None = None
    agent_analysis: str
    urgency: str
    suggested_actions: list[dict]
    status: str = "pending"
    chosen_action_id: str | None = None
    chosen_at: datetime | None = None
    created_at: datetime
    expires_at: datetime | None = None


class AgentEvent(BaseModel):
    event_id: str
    event_type: str
    user_id: str
    payload: dict
    received_at: datetime
    source_ref: str | None = None
