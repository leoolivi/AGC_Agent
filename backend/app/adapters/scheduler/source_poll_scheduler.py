"""Source poll scheduler — APScheduler integration with SourceMonitorService."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.adapters.dummy.source_monitor import DummySourceMonitorAdapter
from app.config import settings
from app.core.services.source_monitor_service import SourceMonitorService
from app.db.models import MonitoredSource
from app.db.session import build_session_factory

if TYPE_CHECKING:
    from app.core.domain.source import SourceConfig

logger = structlog.get_logger()


class SourcePollScheduler:
    """Manage per-source polling jobs via APScheduler."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._job_prefix = "source-poll-"
        self._session_factory = build_session_factory(settings.database_url)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("source_poll_scheduler_started")

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("source_poll_scheduler_stopped")

    async def register_all_active_sources(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(MonitoredSource).where(MonitoredSource.status == "active")
            )
            for source in result.scalars().all():
                await self.register_source(source.id, source.source_type, source.config)

    async def register_source(
        self,
        source_id: uuid.UUID,
        source_type: str,
        config: dict,
    ) -> None:
        interval_minutes = config.get("polling_interval_minutes", settings.source_poll_interval_minutes)
        if source_type == "calendar":
            interval_minutes = settings.calendar_poll_interval_minutes

        job_id = f"{self._job_prefix}{source_id}"
        self._scheduler.add_job(
            self._poll_job,
            trigger="interval",
            minutes=interval_minutes,
            id=job_id,
            replace_existing=True,
            args=[str(source_id)],
        )
        logger.info("source_poll_job_registered", source_id=str(source_id), interval=interval_minutes)

    def remove_source(self, source_id: uuid.UUID) -> None:
        job_id = f"{self._job_prefix}{source_id}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

    async def _poll_job(self, source_id: str) -> None:
        async with self._session_factory() as session:
            monitor = DummySourceMonitorAdapter()
            service = SourceMonitorService(session, monitor)
            try:
                await service.poll_source(uuid.UUID(source_id))
            except Exception as e:
                logger.warning("scheduled_poll_failed", source_id=source_id, error=str(e))


_source_poll_scheduler: SourcePollScheduler | None = None


def get_source_poll_scheduler() -> SourcePollScheduler:
    global _source_poll_scheduler
    if _source_poll_scheduler is None:
        _source_poll_scheduler = SourcePollScheduler()
    return _source_poll_scheduler
