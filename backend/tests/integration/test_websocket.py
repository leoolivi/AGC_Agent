"""Integration tests for WebSocket endpoints."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.services.auth_service import create_access_token
from app.main import app

USER_ID = str(uuid.uuid4())
TOKEN = create_access_token(USER_ID, "test@example.com")
client = TestClient(app)


class TestWebSocket:
    def test_connection_with_valid_jwt(self) -> None:
        with client.websocket_connect(f"/ws/events?token={TOKEN}") as ws:
            ws.send_text("ping")
            data = ws.receive_text()
            assert "pong" in data

    def test_connection_rejected_invalid_token(self) -> None:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/events?token=invalid"):
                pass

    def test_processing_feed_endpoint(self) -> None:
        with client.websocket_connect(f"/ws/processing-feed?token={TOKEN}") as ws:
            ws.send_text("ping")
            assert "pong" in ws.receive_text()
