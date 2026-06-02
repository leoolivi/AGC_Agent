"""Dummy realtime adapter for testing."""
from __future__ import annotations

from app.core.domain.realtime import RealtimeEvent
from app.core.ports.realtime import RealtimePort


class DummyRealtimeAdapter:
    """In-memory RealtimePort that collects emitted events."""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, RealtimeEvent]] = []
        self.broadcasts: list[RealtimeEvent] = []

    async def emit(self, user_id: str, event: RealtimeEvent) -> None:
        self.emitted.append((user_id, event))

    async def broadcast(self, event: RealtimeEvent) -> None:
        self.broadcasts.append(event)

    def clear(self) -> None:
        self.emitted.clear()
        self.broadcasts.clear()


def _assert_protocol() -> None:
    _: RealtimePort = DummyRealtimeAdapter()  # type: ignore[assignment]


_assert_protocol()
