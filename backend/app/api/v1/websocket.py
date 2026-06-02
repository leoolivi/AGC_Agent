"""WebSocket endpoints for real-time events."""
from __future__ import annotations

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.services.auth_service import decode_access_token

router = APIRouter(tags=["websocket"])

from app.adapters.realtime.websocket_adapter import WebSocketRealtimeAdapter

_realtime_adapter = WebSocketRealtimeAdapter()


def get_realtime_adapter() -> WebSocketRealtimeAdapter:
    return _realtime_adapter


async def _handle_ws(websocket: WebSocket, token: str) -> None:
    try:
        payload = decode_access_token(token)
    except JWTError:
        await websocket.close(code=1008, reason="Token invalid or expired")
        return
    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=1008, reason="Token invalid or expired")
        return
    adapter = get_realtime_adapter()
    await adapter.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await adapter.disconnect(user_id, websocket)


@router.websocket("/ws/processing-feed")
async def processing_feed_ws(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    await _handle_ws(websocket, token)


@router.websocket("/ws/events")
async def events_ws(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    await _handle_ws(websocket, token)
