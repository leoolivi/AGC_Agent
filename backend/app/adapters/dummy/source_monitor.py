"""Dummy source monitor adapter for testing without Google API."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from app.core.domain.source import ChangeSet, FileChange, SourceConfig
from app.core.ports.source_monitor import SourceMonitorPort


class DummySourceMonitorAdapter:
    """In-memory SourceMonitorPort for unit tests."""

    def __init__(self) -> None:
        self.changesets: list[ChangeSet] = []
        self.files: dict[str, bytes] = {}
        self.sync_tokens: dict[str, str | None] = {}

    def seed_changes(
        self,
        source_id: str,
        files: list[FileChange],
        sync_token: str | None = "token-1",
    ) -> None:
        self.changesets.append(ChangeSet(new_files=files, new_sync_token=sync_token))
        self.sync_tokens[source_id] = sync_token

    def seed_file(self, file_ref: str, content: bytes) -> None:
        self.files[file_ref] = content

    async def list_changes(
        self,
        source_config: SourceConfig,
        sync_token: str | None,
    ) -> ChangeSet:
        if self.changesets:
            return self.changesets.pop(0)
        return ChangeSet(new_files=[], new_sync_token=sync_token)

    async def download_file(
        self,
        source_type: Literal["drive", "gmail", "calendar"],
        file_ref: str,
    ) -> bytes:
        if file_ref not in self.files:
            return b"dummy file content"
        return self.files[file_ref]


def _assert_protocol() -> None:
    _: SourceMonitorPort = DummySourceMonitorAdapter()  # type: ignore[assignment]


_assert_protocol()
