"""GoogleCalendarAdapter — stub implementation of CalendarPort.

[TODO: TD-002] Replace with real Google Calendar API integration.
Requires: google-auth, google-api-python-client
Setup: OAuth2 credentials + calendar ID in settings.
"""
from __future__ import annotations

import uuid

import structlog

from app.core.ports.calendar import CalendarEvent, CalendarPort

logger = structlog.get_logger()


class GoogleCalendarAdapter(CalendarPort):
    """Stub: logs operations and returns fake event IDs."""

    async def create_event(self, event: CalendarEvent, user_id: str) -> str:
        event_id = f"gcal-stub-{uuid.uuid4().hex[:8]}"
        logger.info(
            "calendar_stub_create",
            event_id=event_id,
            title=event.title,
            due=str(event.due_datetime),
            user_id=user_id,
        )
        return event_id

    async def delete_event(self, event_id: str, user_id: str) -> bool:
        logger.info("calendar_stub_delete", event_id=event_id, user_id=user_id)
        return True
