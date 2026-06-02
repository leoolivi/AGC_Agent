"""
RealtimePort — Protocol for real-time event emission to connected clients.

Implementations: WebSocketRealtimeAdapter (app/adapters/realtime/).
Wiring: app/api/deps.py.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.domain.realtime import RealtimeEvent


@runtime_checkable
class RealtimePort(Protocol):
    """Port for emitting real-time events to connected clients.

    Supports both user-specific events (routed to a single user's connection)
    and broadcast events (sent to all connected clients).

    Used for:
    - Processing feed updates (document ingestion status)
    - Inbox item notifications (new AgentInboxItem created)
    - Source status changes (monitored source connection state)
    - General notifications

    Rate limiting and event aggregation are handled by the adapter
    implementation to prevent overwhelming clients with rapid updates.
    """

    async def emit(self, user_id: str, event: RealtimeEvent) -> None:
        """Emit an event to a specific user's connection.

        Args:
            user_id: Target user identifier
            event: Event to emit with type, payload, and timestamp

        The adapter is responsible for:
        - Finding the user's active WebSocket/SSE connection
        - Serializing the event
        - Handling disconnected clients gracefully
        - Rate limiting (max 1 event/second per resource type)
        """
        ...

    async def broadcast(self, event: RealtimeEvent) -> None:
        """Broadcast an event to all connected clients.

        Args:
            event: Event to broadcast (user_id should be None)

        Used for system-wide notifications or status updates that affect
        all users. The adapter sends to all active connections.
        """
        ...
