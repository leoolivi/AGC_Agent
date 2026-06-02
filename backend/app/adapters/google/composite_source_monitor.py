"""Composite source monitor adapter that routes to Drive, Gmail, or Calendar."""

from __future__ import annotations

from typing import Literal

import structlog

from app.adapters.google.calendar_monitor_adapter import CalendarMonitorAdapter
from app.adapters.google.drive_monitor_adapter import GoogleDriveMonitorAdapter
from app.adapters.google.gmail_monitor_adapter import GmailMonitorAdapter
from app.core.domain.source import ChangeSet, SourceConfig
from app.core.ports.source_monitor import SourceMonitorPort

logger = structlog.get_logger()


class CompositeSourceMonitorAdapter(SourceMonitorPort):
    """Routes source monitoring requests to the appropriate Google API adapter."""

    def __init__(self) -> None:
        """Initialize all Google API adapters."""
        self._drive = GoogleDriveMonitorAdapter()
        self._gmail = GmailMonitorAdapter()
        self._calendar = CalendarMonitorAdapter()

    async def list_changes(
        self,
        source_config: SourceConfig,
        sync_token: str | None,
    ) -> ChangeSet:
        """Route to appropriate adapter based on source type.

        Args:
            source_config: Source configuration with type and settings.
            sync_token: Optional sync token for incremental changes.

        Returns:
            ChangeSet with new files and updated sync token.

        Raises:
            ValueError: If source_type is not supported.
        """
        source_type = source_config.source_type

        if source_type == "drive":
            return await self._drive.list_changes(source_config, sync_token)
        elif source_type == "gmail":
            return await self._gmail.list_changes(source_config, sync_token)
        elif source_type == "calendar":
            return await self._calendar.list_changes(source_config, sync_token)
        else:
            msg = f"Unsupported source type: {source_type}"
            raise ValueError(msg)

    async def download_file(
        self,
        source_type: Literal["drive", "gmail", "calendar"],
        file_ref: str,
    ) -> bytes:
        """Route file download to appropriate adapter.

        Args:
            source_type: Type of source (drive, gmail, calendar).
            file_ref: Reference to the file (file_id, message_id, event_id).

        Returns:
            File content as bytes.

        Raises:
            ValueError: If source_type is not supported.
        """
        if source_type == "drive":
            return await self._drive.download_file(source_type, file_ref)
        elif source_type == "gmail":
            return await self._gmail.download_file(source_type, file_ref)
        elif source_type == "calendar":
            # Calendar events don't have downloadable files
            msg = "Calendar events cannot be downloaded as files"
            raise ValueError(msg)
        else:
            msg = f"Unsupported source type: {source_type}"
            raise ValueError(msg)
