"""Google Calendar monitor adapter implementing SourceMonitorPort."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

import structlog
from googleapiclient.discovery import build

from app.adapters.google.credentials import get_credentials
from app.core.domain.source import CalendarSourceConfig, ChangeSet, FileChange, SourceConfig

logger = structlog.get_logger()


class CalendarMonitorAdapter:
    """Poll Google Calendar for upcoming events using sync tokens."""

    async def list_changes(
        self,
        source_config: SourceConfig,
        sync_token: str | None,
    ) -> ChangeSet:
        if not isinstance(source_config.config, CalendarSourceConfig):
            msg = "Expected CalendarSourceConfig"
            raise ValueError(msg)

        cal_config = source_config.config
        user_id = str(source_config.user_id)

        try:
            creds = await get_credentials(user_id)
            service = build("calendar", "v3", credentials=creds)

            now = datetime.now(UTC)
            time_max = now + timedelta(days=cal_config.lookahead_days)

            kwargs: dict = {
                "calendarId": cal_config.calendar_id,
                "timeMin": now.isoformat(),
                "timeMax": time_max.isoformat(),
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 100,
            }

            if sync_token:
                kwargs["syncToken"] = sync_token
                del kwargs["timeMin"]
                del kwargs["timeMax"]

            result = service.events().list(**kwargs).execute()
            events = result.get("items", [])
            new_token = result.get("nextSyncToken")

            changes = [self._event_to_file_change(e) for e in events]
            return ChangeSet(new_files=changes, new_sync_token=new_token)

        except Exception as e:
            if sync_token and ("410" in str(e) or "Sync token" in str(e)):
                logger.warning("calendar_sync_token_expired", error=str(e))
                return await self.list_changes(source_config, None)
            logger.error("calendar_list_changes_failed", error=str(e))
            raise RuntimeError(f"Calendar API failed: {e}") from e

    async def download_file(
        self,
        source_type: Literal["drive", "gmail", "calendar"],
        file_ref: str,
    ) -> bytes:
        if source_type != "calendar":
            msg = f"CalendarMonitorAdapter only supports calendar, got {source_type}"
            raise ValueError(msg)

        creds = await get_credentials("")
        service = build("calendar", "v3", credentials=creds)
        event = service.events().get(calendarId="primary", eventId=file_ref).execute()

        import json

        metadata = {
            "event_id": event.get("id"),
            "title": event.get("summary", ""),
            "description": event.get("description", ""),
            "start": event.get("start", {}),
            "end": event.get("end", {}),
            "participants": [
                a.get("email", "") for a in event.get("attendees", [])
            ],
        }
        return json.dumps(metadata, ensure_ascii=False).encode("utf-8")

    def _event_to_file_change(self, event: dict) -> FileChange:
        start = event.get("start", {})
        start_str = start.get("dateTime") or start.get("date", "")
        try:
            modified_at = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            modified_at = datetime.now(UTC)

        title = event.get("summary", "Evento senza titolo")
        participants = ", ".join(
            a.get("email", "") for a in event.get("attendees", [])
        )
        description = event.get("description", "")

        return FileChange(
            file_id=event["id"],
            filename=f"{title}|{participants}|{description[:100]}",
            mime_type="application/vnd.google.calendar.event",
            modified_at=modified_at,
        )
