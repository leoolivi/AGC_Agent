"""Unit tests for SourceMonitorService."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.dummy.source_monitor import DummySourceMonitorAdapter
from app.core.domain.source import ChangeSet, DriveSourceConfig, FileChange, SourceConfig
from app.core.services.source_monitor_service import MAX_FILES_PER_CYCLE, SourceMonitorService


def _make_source_orm(source_id: uuid.UUID | None = None) -> MagicMock:
    sid = source_id or uuid.uuid4()
    orm = MagicMock()
    orm.id = sid
    orm.user_id = uuid.uuid4()
    orm.source_type = "drive"
    orm.config = {"folder_id": "f1", "folder_name": "Test", "polling_interval_minutes": 15}
    orm.status = "active"
    orm.last_sync_token = None
    orm.last_sync_at = None
    orm.last_sync_count = 0
    orm.error_count = 0
    return orm


def _make_file_change(i: int) -> FileChange:
    return FileChange(
        file_id=f"file-{i}",
        filename=f"doc-{i}.pdf",
        mime_type="application/pdf",
        modified_at=datetime.now(UTC),
    )


@pytest.fixture
def dummy_monitor() -> DummySourceMonitorAdapter:
    return DummySourceMonitorAdapter()


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestSourceMonitorService:
    @pytest.mark.asyncio
    async def test_poll_source_updates_sync_token(
        self, mock_session: AsyncMock, dummy_monitor: DummySourceMonitorAdapter
    ) -> None:
        source = _make_source_orm()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = source
        mock_session.execute.return_value = mock_result

        files = [_make_file_change(i) for i in range(3)]
        dummy_monitor.changesets.append(
            ChangeSet(new_files=files, new_sync_token="new-token-123")
        )

        service = SourceMonitorService(mock_session, dummy_monitor)
        result = await service.poll_source(source.id)

        assert len(result.new_files) == 3
        assert source.last_sync_token == "new-token-123"
        assert source.error_count == 0

    @pytest.mark.asyncio
    async def test_batch_limiting(
        self, mock_session: AsyncMock, dummy_monitor: DummySourceMonitorAdapter
    ) -> None:
        source = _make_source_orm()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = source
        mock_session.execute.return_value = mock_result

        files = [_make_file_change(i) for i in range(15)]
        dummy_monitor.changesets.append(
            ChangeSet(new_files=files, new_sync_token="token-after-batch")
        )

        service = SourceMonitorService(mock_session, dummy_monitor)
        result = await service.poll_source(source.id)

        assert len(result.new_files) == MAX_FILES_PER_CYCLE
        assert source.last_sync_token is None

    @pytest.mark.asyncio
    async def test_error_counting_and_suspension(
        self, mock_session: AsyncMock,
    ) -> None:
        source = _make_source_orm()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = source
        mock_session.execute.return_value = mock_result

        failing_monitor = AsyncMock()
        failing_monitor.list_changes = AsyncMock(side_effect=RuntimeError("API down"))

        service = SourceMonitorService(mock_session, failing_monitor)

        for i in range(2):
            with pytest.raises(RuntimeError):
                await service.poll_source(source.id)
            assert source.error_count == i + 1
            assert source.status == "active"

        with pytest.raises(RuntimeError):
            await service.poll_source(source.id)
        assert source.error_count == 3
        assert source.status == "error"
