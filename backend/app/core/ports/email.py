"""
EmailSenderPort — Protocol for email sending backends.

Implementations: SMTPAdapter (app/adapters/email/).
Wiring: app/api/deps.py via EMAIL_BACKEND env var.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body_html: str
    body_text: str
    reply_to: str | None = None


@runtime_checkable
class EmailSenderPort(Protocol):
    async def send(self, message: EmailMessage) -> bool: ...

    async def send_draft(self, draft_id: str) -> bool: ...
