"""Dummy escalation scheduler for testing."""
from __future__ import annotations

import uuid

from app.core.ports.escalation_scheduler import EscalationSchedulerPort


class DummyEscalationSchedulerAdapter:
    """In-memory EscalationSchedulerPort for unit tests."""

    def __init__(self) -> None:
        self.scheduled: list[tuple[str, int, str]] = []
        self.cancelled: list[str] = []

    async def schedule_step(self, escalation_id: str, delay_seconds: int) -> str:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self.scheduled.append((escalation_id, delay_seconds, job_id))
        return job_id

    async def cancel_step(self, job_id: str) -> None:
        active_ids = [s[2] for s in self.scheduled if s[2] not in self.cancelled]
        if job_id not in active_ids:
            msg = f"Job {job_id} not found"
            raise ValueError(msg)
        self.cancelled.append(job_id)


def _assert_protocol() -> None:
    _: EscalationSchedulerPort = DummyEscalationSchedulerAdapter()  # type: ignore[assignment]


_assert_protocol()
