"""NotificationService — dispatches notifications via configured channels."""
from __future__ import annotations

import structlog

from app.core.ports.notifier import NotifierPort

logger = structlog.get_logger()


class NotificationService:
    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    async def dispatch(
        self,
        user_id: str,
        title: str,
        body: str,
        level: str = "info",
        channels: list[str] | None = None,
    ) -> bool:
        """Dispatch notification to configured channels based on level."""
        channels = channels or self._channels_for_level(level)
        success = True
        for channel in channels:
            if channel == "inapp":
                ok = await self._notifier.send_inapp(user_id, title, body, level)
            elif channel == "email":
                ok = await self._notifier.send_email_notification(user_id, title, body)
            else:
                ok = False
            if not ok:
                success = False
                logger.warning("notification_failed", channel=channel, user_id=user_id)
        return success

    def _channels_for_level(self, level: str) -> list[str]:
        if level in ("urgent", "action"):
            return ["inapp", "email"]
        if level == "warning":
            return ["inapp"]
        return ["inapp"]
