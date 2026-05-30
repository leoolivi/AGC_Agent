"""
DummyEmailAdapter — in-memory implementation of EmailSenderPort.

Records sent messages in a list for assertion in tests.
No SMTP calls. Safe to use in unit tests.
"""
from __future__ import annotations

from app.core.ports.email import EmailMessage, EmailSenderPort


class DummyEmailAdapter:
    """In-memory EmailSenderPort implementation for testing."""

    def __init__(self) -> None:
        self.sent_messages: list[EmailMessage] = []
        self.sent_draft_ids: list[str] = []

    async def send(self, message: EmailMessage) -> bool:
        self.sent_messages.append(message)
        return True

    async def send_draft(self, draft_id: str) -> bool:
        self.sent_draft_ids.append(draft_id)
        return True


# Verify structural compatibility at import time.
def _assert_protocol() -> None:
    _: EmailSenderPort = DummyEmailAdapter()  # type: ignore[assignment]


_assert_protocol()
