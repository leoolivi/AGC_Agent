"""
CalendarPort — Protocol for calendar integration backends.

[TODO: TD-002] Google Calendar real implementation is DEFERRED.
The stub in app/adapters/dummy/ is the only implementation for Phase 0-2.
Wiring: app/api/deps.py via CALENDAR_BACKEND env var.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class CalendarEvent:
    title: str
    due_datetime: datetime
    description: str
    external_id: str | None = None


@runtime_checkable
class CalendarPort(Protocol):
    async def create_event(
        self,
        event: CalendarEvent,
        user_id: str,
    ) -> str: ...  # Returns event_id

    async def delete_event(
        self,
        event_id: str,
        user_id: str,
    ) -> bool: ...
