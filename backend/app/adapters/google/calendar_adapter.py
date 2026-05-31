"""Google Calendar adapter — real implementation."""
from __future__ import annotations

import structlog
from googleapiclient.discovery import build

from app.adapters.google.credentials import get_credentials
from app.core.ports.calendar import CalendarEvent, CalendarPort

logger = structlog.get_logger()


class GoogleCalendarRealAdapter(CalendarPort):
    """Create and delete events via Google Calendar API."""

    async def create_event(self, event: CalendarEvent, user_id: str) -> str:
        try:
            creds = await get_credentials(user_id)
            service = build("calendar", "v3", credentials=creds)

            body = {
                "summary": event.title,
                "description": event.description,
                "start": {"dateTime": event.due_datetime.isoformat(), "timeZone": "Europe/Rome"},
                "end": {"dateTime": event.due_datetime.isoformat(), "timeZone": "Europe/Rome"},
                "reminders": {"useDefault": True},
            }
            result = service.events().insert(calendarId="primary", body=body).execute()
            event_id = result["id"]
            logger.info("calendar_event_created", event_id=event_id, title=event.title)
            return event_id
        except Exception as e:
            logger.error("calendar_create_failed", error=str(e))
            raise

    async def delete_event(self, event_id: str, user_id: str) -> bool:
        try:
            creds = await get_credentials(user_id)
            service = build("calendar", "v3", credentials=creds)
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            logger.info("calendar_event_deleted", event_id=event_id)
            return True
        except Exception as e:
            logger.error("calendar_delete_failed", error=str(e))
            return False
