"""APScheduler escalation adapter implementing EscalationSchedulerPort."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.ports.escalation_scheduler import EscalationSchedulerPort

logger = structlog.get_logger()

MIN_DELAY = 3600
MAX_DELAY = 604800


class APSchedulerEscalationAdapter:
    """Schedule escalation step transitions using APScheduler."""

    def __init__(
        self,
        scheduler: AsyncIOScheduler | None = None,
        step_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._scheduler = scheduler or AsyncIOScheduler()
        self._step_callback = step_callback
        self._job_map: dict[str, str] = {}
        if not self._scheduler.running:
            self._scheduler.start()

    def set_step_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        self._step_callback = callback

    async def schedule_step(self, escalation_id: str, delay_seconds: int) -> str:
        if delay_seconds < MIN_DELAY or delay_seconds > MAX_DELAY:
            msg = f"delay_seconds must be between {MIN_DELAY} and {MAX_DELAY}"
            raise ValueError(msg)

        job_id = f"escalation-{escalation_id}-{uuid.uuid4().hex[:8]}"

        async def _run() -> None:
            if self._step_callback:
                await self._step_callback(escalation_id)
            self._job_map.pop(job_id, None)

        from datetime import UTC, datetime, timedelta

        run_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        self._scheduler.add_job(
            _run,
            trigger="date",
            run_date=run_at,
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
        )

        self._job_map[job_id] = escalation_id
        logger.info("escalation_step_scheduled", job_id=job_id, escalation_id=escalation_id, delay=delay_seconds)
        return job_id

    async def cancel_step(self, job_id: str) -> None:
        if job_id not in self._job_map and not self._scheduler.get_job(job_id):
            msg = f"Job {job_id} not found"
            raise ValueError(msg)
        try:
            self._scheduler.remove_job(job_id)
        except Exception as e:
            msg = f"Job {job_id} not found or already executed"
            raise ValueError(msg) from e
        self._job_map.pop(job_id, None)
        logger.info("escalation_step_cancelled", job_id=job_id)

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)


def _assert_protocol() -> None:
    _: EscalationSchedulerPort = APSchedulerEscalationAdapter()  # type: ignore[assignment]


_assert_protocol()
