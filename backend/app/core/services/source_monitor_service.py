"""SourceMonitorService — CRUD for source configurations and polling orchestration.

This service manages monitored sources (Drive folders, Gmail labels, Calendar),
handles sync token persistence, implements error counting with 3-strike suspension,
and enforces max 10 files per cycle batching.

Requirements: 1, 2
Properties: 1, 2, 4, 5, 6
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.source import (
    CalendarSourceConfig,
    ChangeSet,
    DriveSourceConfig,
    GmailSourceConfig,
    SourceConfig,
)
from app.core.ports.source_monitor import SourceMonitorPort
from app.db.models import MonitoredSource

logger = structlog.get_logger()

MAX_FILES_PER_CYCLE = 10
MAX_ERROR_COUNT = 3


class SourceMonitorService:
    """Service for managing monitored sources and orchestrating polling."""

    def __init__(
        self,
        session: AsyncSession,
        source_monitor_port: SourceMonitorPort,
    ) -> None:
        """Initialize the service with database session and source monitor adapter.

        Args:
            session: SQLAlchemy async session for database operations.
            source_monitor_port: Port for interacting with external source providers.
        """
        self._session = session
        self._source_monitor = source_monitor_port

    async def create_source(
        self,
        user_id: uuid.UUID,
        source_type: Literal["drive", "gmail", "calendar"],
        config: DriveSourceConfig | GmailSourceConfig | CalendarSourceConfig,
    ) -> SourceConfig:
        """Create a new monitored source configuration.

        Args:
            user_id: The user who owns this source.
            source_type: Type of source (drive, gmail, calendar).
            config: Source-specific configuration (validated by Pydantic).

        Returns:
            The created SourceConfig domain model.

        Raises:
            ValueError: If config validation fails (handled by Pydantic validators).
        """
        # Pydantic validation happens automatically when config is constructed
        source = MonitoredSource(
            id=uuid.uuid4(),
            user_id=user_id,
            source_type=source_type,
            config=config.model_dump(),
            status="active",
            last_sync_token=None,
            last_sync_at=None,
            last_sync_count=0,
            error_count=0,
        )
        self._session.add(source)
        await self._session.commit()
        await self._session.refresh(source)

        logger.info(
            "source_created",
            source_id=str(source.id),
            user_id=str(user_id),
            source_type=source_type,
        )

        return self._to_domain(source)

    async def get_source(self, source_id: uuid.UUID, user_id: uuid.UUID) -> SourceConfig | None:
        """Retrieve a source configuration by ID.

        Args:
            source_id: The source ID.
            user_id: The user ID (for authorization).

        Returns:
            SourceConfig if found and owned by user, None otherwise.
        """
        result = await self._session.execute(
            select(MonitoredSource)
            .where(MonitoredSource.id == source_id)
            .where(MonitoredSource.user_id == user_id)
        )
        source = result.scalar_one_or_none()
        return self._to_domain(source) if source else None

    async def list_sources(
        self,
        user_id: uuid.UUID,
        source_type: Literal["drive", "gmail", "calendar"] | None = None,
        status: Literal["active", "error", "paused"] | None = None,
    ) -> list[SourceConfig]:
        """List all sources for a user with optional filters.

        Args:
            user_id: The user ID.
            source_type: Optional filter by source type.
            status: Optional filter by status.

        Returns:
            List of SourceConfig domain models.
        """
        query = select(MonitoredSource).where(MonitoredSource.user_id == user_id)

        if source_type:
            query = query.where(MonitoredSource.source_type == source_type)
        if status:
            query = query.where(MonitoredSource.status == status)

        query = query.order_by(MonitoredSource.created_at.desc())

        result = await self._session.execute(query)
        sources = result.scalars().all()
        return [self._to_domain(s) for s in sources]

    async def update_source(
        self,
        source_id: uuid.UUID,
        user_id: uuid.UUID,
        config: DriveSourceConfig | GmailSourceConfig | CalendarSourceConfig | None = None,
        status: Literal["active", "error", "paused"] | None = None,
    ) -> SourceConfig | None:
        """Update a source configuration.

        Args:
            source_id: The source ID.
            user_id: The user ID (for authorization).
            config: Optional new configuration.
            status: Optional new status.

        Returns:
            Updated SourceConfig if found and owned by user, None otherwise.
        """
        result = await self._session.execute(
            select(MonitoredSource)
            .where(MonitoredSource.id == source_id)
            .where(MonitoredSource.user_id == user_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return None

        if config:
            source.config = config.model_dump()
        if status:
            source.status = status

        source.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(source)

        logger.info(
            "source_updated",
            source_id=str(source_id),
            user_id=str(user_id),
            status=status,
        )

        return self._to_domain(source)

    async def delete_source(self, source_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a source configuration.

        Args:
            source_id: The source ID.
            user_id: The user ID (for authorization).

        Returns:
            True if deleted, False if not found or not owned by user.
        """
        result = await self._session.execute(
            select(MonitoredSource)
            .where(MonitoredSource.id == source_id)
            .where(MonitoredSource.user_id == user_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return False

        await self._session.delete(source)
        await self._session.commit()

        logger.info("source_deleted", source_id=str(source_id), user_id=str(user_id))
        return True

    async def poll_source(self, source_id: uuid.UUID) -> ChangeSet:
        """Poll a source for new changes and update sync state.

        This method:
        1. Retrieves the source configuration and sync token
        2. Calls the source monitor adapter to list changes
        3. Enforces max 10 files per cycle batching (Property 6)
        4. Updates sync token and last_sync_at on success
        5. Increments error_count and suspends after 3 failures (Property 5)

        Args:
            source_id: The source ID to poll.

        Returns:
            ChangeSet with new files (max 10) and updated sync token.

        Raises:
            ValueError: If source not found or not active.
            RuntimeError: If polling fails and error count reaches threshold.
        """
        result = await self._session.execute(
            select(MonitoredSource).where(MonitoredSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            msg = f"Source {source_id} not found"
            raise ValueError(msg)

        if source.status == "paused":
            msg = f"Source {source_id} is paused"
            raise ValueError(msg)

        # Convert DB model to domain model
        source_config = self._to_domain(source)

        try:
            # Call adapter to list changes
            changeset = await self._source_monitor.list_changes(
                source_config=source_config,
                sync_token=source.last_sync_token,
            )

            # Enforce max 10 files per cycle (Property 6)
            if len(changeset.new_files) > MAX_FILES_PER_CYCLE:
                logger.info(
                    "batch_limit_applied",
                    source_id=str(source_id),
                    total_files=len(changeset.new_files),
                    processed=MAX_FILES_PER_CYCLE,
                )
                # Keep only first 10 files, don't update sync token
                # so remaining files are picked up in next cycle
                changeset = ChangeSet(
                    new_files=changeset.new_files[:MAX_FILES_PER_CYCLE],
                    new_sync_token=source.last_sync_token,  # Keep old token
                )
            else:
                # Update sync token only if we processed all files
                if changeset.new_sync_token:
                    source.last_sync_token = changeset.new_sync_token

            # Update success state (Property 4 - sync token idempotency)
            source.last_sync_at = datetime.now(UTC)
            source.last_sync_count = len(changeset.new_files)
            source.error_count = 0  # Reset error count on success
            if source.status == "error":
                source.status = "active"  # Recover from error state

            await self._session.commit()

            logger.info(
                "source_polled",
                source_id=str(source_id),
                files_found=len(changeset.new_files),
                sync_token_updated=changeset.new_sync_token is not None,
            )

            return changeset

        except Exception as e:
            # Increment error count (Property 5 - 3-strike suspension)
            source.error_count += 1

            if source.error_count >= MAX_ERROR_COUNT:
                source.status = "error"
                logger.warning(
                    "source_suspended",
                    source_id=str(source_id),
                    error_count=source.error_count,
                    error=str(e),
                )
            else:
                logger.warning(
                    "source_poll_failed",
                    source_id=str(source_id),
                    error_count=source.error_count,
                    error=str(e),
                )

            await self._session.commit()
            raise

    async def reset_error_count(self, source_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Reset error count and reactivate a source in error state.

        This is typically called when a user manually reconnects OAuth
        or fixes the underlying issue.

        Args:
            source_id: The source ID.
            user_id: The user ID (for authorization).

        Returns:
            True if reset, False if not found or not owned by user.
        """
        result = await self._session.execute(
            select(MonitoredSource)
            .where(MonitoredSource.id == source_id)
            .where(MonitoredSource.user_id == user_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return False

        source.error_count = 0
        if source.status == "error":
            source.status = "active"
        source.updated_at = datetime.now(UTC)

        await self._session.commit()

        logger.info("source_error_reset", source_id=str(source_id), user_id=str(user_id))
        return True

    def _to_domain(self, source: MonitoredSource) -> SourceConfig:
        """Convert ORM model to domain model.

        Args:
            source: SQLAlchemy ORM model.

        Returns:
            SourceConfig domain model with properly typed config.
        """
        # Parse config based on source_type
        config: DriveSourceConfig | GmailSourceConfig | CalendarSourceConfig
        if source.source_type == "drive":
            config = DriveSourceConfig(**source.config)
        elif source.source_type == "gmail":
            config = GmailSourceConfig(**source.config)
        elif source.source_type == "calendar":
            config = CalendarSourceConfig(**source.config)
        else:
            msg = f"Unknown source_type: {source.source_type}"
            raise ValueError(msg)

        return SourceConfig(
            id=source.id,
            user_id=source.user_id,
            source_type=source.source_type,  # type: ignore[arg-type]
            config=config,
            status=source.status,  # type: ignore[arg-type]
            last_sync_at=source.last_sync_at,
            last_sync_count=source.last_sync_count,
        )
