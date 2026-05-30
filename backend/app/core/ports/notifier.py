"""
NotifierPort — Protocol for notification dispatch backends.

Implementations: InAppNotifier, EmailNotifier (app/adapters/notifier/).
Wiring: app/api/deps.py.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NotifierPort(Protocol):
    async def send_inapp(
        self,
        user_id: str,
        title: str,
        body: str,
        level: str,
    ) -> bool: ...

    async def send_email_notification(
        self,
        user_id: str,
        subject: str,
        body: str,
    ) -> bool: ...
