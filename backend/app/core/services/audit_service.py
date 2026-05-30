"""AuditService — INSERT-only audit log. Never UPDATE/DELETE."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


class AuditService:
    """Append-only audit log service."""

    def __init__(self) -> None:
        self._entries: list[dict] = []  # In-memory for testing; DB in production

    def log(
        self,
        action_type: str,
        user_id: str | None = None,
        session_id: str | None = None,
        tool_name: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        risk_score: int | None = None,
        status: str | None = None,
        llm_model: str | None = None,
    ) -> dict:
        """Append an audit entry. Never logs secret values."""
        entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "action_type": action_type,
            "tool_name": tool_name,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "risk_score": risk_score,
            "status": status,
            "llm_model": llm_model,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._entries.append(entry)
        logger.info("audit_log", action_type=action_type, user_id=user_id)
        return entry

    @property
    def count(self) -> int:
        return len(self._entries)

    def get_entries(
        self,
        action_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Query entries with optional filter. Newest first."""
        entries = self._entries
        if action_type:
            entries = [e for e in entries if e["action_type"] == action_type]
        entries = sorted(entries, key=lambda e: e["created_at"], reverse=True)
        return entries[offset : offset + limit]
