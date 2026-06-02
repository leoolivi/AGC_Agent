"""WebSocket realtime adapter implementing RealtimePort."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import structlog
from fastapi import WebSocket

from app.core.domain.realtime import RealtimeEvent
from app.core.ports.realtime import RealtimePort

logger = structlog.get_logger()

RATE_LIMIT_SECONDS = 1.0


class WebSocketRealtimeAdapter:
    """Manage WebSocket connections with per-user channels and rate limiting."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._last_emit: dict[str, datetime] = {}
        self._pending_aggregates: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].append(websocket)
        logger.info("websocket_connected", user_id=user_id)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self._connections.pop(user_id, None)
        logger.info("websocket_disconnected", user_id=user_id)

    async def emit(self, user_id: str, event: RealtimeEvent) -> None:
        rate_key = f"{user_id}:{event.event_type}"
        now = datetime.now()

        if not self._should_emit(rate_key, now):
            self._pending_aggregates[rate_key] = event.payload
            return

        payload = event.payload
        if rate_key in self._pending_aggregates:
            payload = {**self._pending_aggregates.pop(rate_key), **payload}

        self._last_emit[rate_key] = now
        message = json.dumps({
            "event_type": event.event_type,
            "payload": payload,
            "timestamp": event.timestamp.isoformat(),
        })

        async with self._lock:
            conns = list(self._connections.get(user_id, []))

        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(user_id, ws)

    async def broadcast(self, event: RealtimeEvent) -> None:
        async with self._lock:
            user_ids = list(self._connections.keys())
        for uid in user_ids:
            user_event = RealtimeEvent(
                event_type=event.event_type,
                payload=event.payload,
                timestamp=event.timestamp,
                user_id=uid,
            )
            await self.emit(uid, user_event)

    def _should_emit(self, rate_key: str, now: datetime) -> bool:
        last = self._last_emit.get(rate_key)
        if last is None:
            return True
        return (now - last).total_seconds() >= RATE_LIMIT_SECONDS

    @property
    def connection_count(self) -> int:
        return sum(len(c) for c in self._connections.values())


def _assert_protocol() -> None:
    _: RealtimePort = WebSocketRealtimeAdapter()  # type: ignore[assignment]


_assert_protocol()
