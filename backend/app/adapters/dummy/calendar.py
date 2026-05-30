"""
DummyCalendarAdapter — stub implementation of CalendarPort.

[TODO: TD-002] Real Google Calendar integration is DEFERRED.
Records created/deleted events in memory for test assertions.
No external dependencies. Safe to use in unit tests.
"""
from __future__ import annotations

import uuid

from app.core.ports.calendar import CalendarEvent, CalendarPort


class DummyCalendarAdapter:
    """Stub CalendarPort implementation — TD-002 deferred."""

    def __init__(self) -> None:
        self.created_events: dict[str, tuple[CalendarEvent, str]] = {}
        self.deleted_event_ids: list[str] = []

    async def create_event(
        self,
        event: CalendarEvent,
        user_id: str,
    ) -> str:
        # [TODO: TD-002] Replace with real Google Calendar API call.
        event_id = str(uuid.uuid4())
        self.created_events[event_id] = (event, user_id)
        return event_id

    async def delete_event(
        self,
        event_id: str,
        user_id: str,
    ) -> bool:
        # [TODO: TD-002] Replace with real Google Calendar API call.
        if event_id not in self.created_events:
            return False
        del self.created_events[event_id]
        self.deleted_event_ids.append(event_id)
        return True


# Verify structural compatibility at import time.
def _assert_protocol() -> None:
    _: CalendarPort = DummyCalendarAdapter()  # type: ignore[assignment]


_assert_protocol()
