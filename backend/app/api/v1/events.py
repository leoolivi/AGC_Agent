"""SSE fallback endpoint for real-time events."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.adapters.dummy.realtime import DummyRealtimeAdapter

router = APIRouter(prefix="/events", tags=["events"])

_sse_subscribers: dict[str, asyncio.Queue[str]] = {}
_realtime_adapter: DummyRealtimeAdapter | None = None


def get_sse_adapter() -> DummyRealtimeAdapter:
    global _realtime_adapter
    if _realtime_adapter is None:
        _realtime_adapter = DummyRealtimeAdapter()
    return _realtime_adapter


async def _event_generator(user_id: str, request: Request) -> AsyncIterator[str]:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _sse_subscribers[user_id] = queue

    try:
        yield f"data: {json.dumps({'event_type': 'connected', 'payload': {}})}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {message}\n\n"
            except TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        _sse_subscribers.pop(user_id, None)


@router.get("/stream")
async def events_stream(
    request: Request,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """SSE fallback for environments where WebSocket is unavailable."""
    user_id = user["sub"]
    return StreamingResponse(
        _event_generator(user_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def push_sse_event(user_id: str, event_type: str, payload: dict) -> None:
    """Push an event to an SSE subscriber if connected."""
    queue = _sse_subscribers.get(user_id)
    if queue:
        message = json.dumps({"event_type": event_type, "payload": payload})
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass
