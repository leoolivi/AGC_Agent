"""
SourceMonitorPort — Protocol for polling external sources for new content.

Implementations: GoogleDriveMonitorAdapter, GmailMonitorAdapter,
CalendarMonitorAdapter (app/adapters/google/).
Wiring: app/api/deps.py via dependency injection.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from app.core.domain.source import ChangeSet, SourceConfig


@runtime_checkable
class SourceMonitorPort(Protocol):
    """Port for monitoring external sources (Drive, Gmail, Calendar) for changes."""

    async def list_changes(
        self,
        source_config: SourceConfig,
        sync_token: str | None,
    ) -> ChangeSet:
        """
        Poll a source for new or modified files/events since the last sync.

        Args:
            source_config: The source configuration (Drive folder, Gmail label, or Calendar).
            sync_token: Opaque token from the previous sync; None for initial sync.

        Returns:
            ChangeSet containing new files and an updated sync token.

        Raises:
            ValueError: If source_config is invalid or unsupported.
            RuntimeError: If the provider API fails after retries.
        """
        ...

    async def download_file(
        self,
        source_type: Literal["drive", "gmail", "calendar"],
        file_ref: str,
    ) -> bytes:
        """
        Download file content from a source.

        Args:
            source_type: The type of source (drive, gmail, calendar).
            file_ref: Provider-specific file reference (file_id for Drive,
                     message_id for Gmail, event_id for Calendar).

        Returns:
            Raw file content as bytes.

        Raises:
            ValueError: If source_type is unsupported or file_ref is invalid.
            RuntimeError: If the download fails after retries.
        """
        ...
