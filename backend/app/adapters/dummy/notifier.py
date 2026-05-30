"""
DummyNotifierAdapter — in-memory implementation of NotifierPort.

Records dispatched notifications for assertion in tests.
No external dependencies. Safe to use in unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.ports.notifier import NotifierPort


@dataclass
class _InAppRecord:
    user_id: str
    title: str
    body: str
    level: str


@dataclass
class _EmailRecord:
    user_id: str
    subject: str
    body: str


class DummyNotifierAdapter:
    """In-memory NotifierPort implementation for testing."""

    def __init__(self) -> None:
        self.inapp_notifications: list[_InAppRecord] = []
        self.email_notifications: list[_EmailRecord] = []

    async def send_inapp(
        self,
        user_id: str,
        title: str,
        body: str,
        level: str,
    ) -> bool:
        self.inapp_notifications.append(
            _InAppRecord(user_id=user_id, title=title, body=body, level=level)
        )
        return True

    async def send_email_notification(
        self,
        user_id: str,
        subject: str,
        body: str,
    ) -> bool:
        self.email_notifications.append(
            _EmailRecord(user_id=user_id, subject=subject, body=body)
        )
        return True


# Verify structural compatibility at import time.
def _assert_protocol() -> None:
    _: NotifierPort = DummyNotifierAdapter()  # type: ignore[assignment]


_assert_protocol()
