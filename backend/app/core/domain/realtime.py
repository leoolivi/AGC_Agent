"""Real-time event domain model for WebSocket/SSE communication."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class RealtimeEvent(BaseModel):
    """A real-time event emitted to connected clients via WebSocket or SSE.

    Events are multiplexed over a single connection per user. When user_id
    is None, the event is broadcast to all connected clients.
    """

    event_type: Literal[
        "processing_status",
        "inbox_item",
        "notification",
        "source_status",
    ]
    payload: dict[str, Any]
    timestamp: datetime
    user_id: str | None = None  # None for broadcast events
