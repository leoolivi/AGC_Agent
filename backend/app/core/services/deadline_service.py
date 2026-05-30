"""DeadlineService — CRUD + check_and_notify for deadlines."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import structlog

logger = structlog.get_logger()

DEFAULT_NOTIFY_DAYS = [30, 7, 3, 1]


class DeadlineService:
    """In-memory deadline service for Phase 2. Production uses DB."""

    def __init__(self) -> None:
        self._deadlines: list[dict] = []

    def create(
        self,
        user_id: str,
        title: str,
        due_date: date,
        deadline_type: str = "custom",
        recurrence: str = "none",
        source: str = "manual",
        source_confidence: float | None = None,
        document_id: str | None = None,
    ) -> dict:
        deadline = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": document_id,
            "title": title,
            "due_date": due_date.isoformat(),
            "deadline_type": deadline_type,
            "recurrence": recurrence,
            "status": "active",
            "source": source,
            "source_confidence": source_confidence,
            "notified_at": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._deadlines.append(deadline)
        return deadline

    def get_upcoming(self, user_id: str, days: int = 30) -> list[dict]:
        today = date.today()
        cutoff = today + timedelta(days=days)
        return [
            d for d in self._deadlines
            if d["user_id"] == user_id
            and d["status"] == "active"
            and today <= date.fromisoformat(d["due_date"]) <= cutoff
        ]

    def check_and_notify(self, notify_days: list[int] | None = None) -> list[dict]:
        """Check all active deadlines and return those needing notification."""
        notify_days = notify_days or DEFAULT_NOTIFY_DAYS
        today = date.today()
        notifications: list[dict] = []

        for d in self._deadlines:
            if d["status"] != "active":
                continue
            due = date.fromisoformat(d["due_date"])
            days_until = (due - today).days

            if days_until < 0:
                notifications.append({**d, "notification_type": "overdue", "days": abs(days_until)})
            elif days_until in notify_days:
                notifications.append({**d, "notification_type": "approaching", "days": days_until})

        return notifications

    def compute_next_occurrence(self, deadline: dict) -> date | None:
        """Compute next occurrence for recurring deadlines."""
        recurrence = deadline.get("recurrence", "none")
        due = date.fromisoformat(deadline["due_date"])
        if recurrence == "monthly":
            return due.replace(month=due.month % 12 + 1) if due.month < 12 else due.replace(year=due.year + 1, month=1)
        if recurrence == "quarterly":
            month = due.month + 3
            year = due.year + (month - 1) // 12
            return due.replace(year=year, month=(month - 1) % 12 + 1)
        if recurrence == "annual":
            return due.replace(year=due.year + 1)
        return None
