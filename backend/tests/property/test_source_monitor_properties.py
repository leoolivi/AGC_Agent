"""Property-based tests for SourceMonitorService."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.adapters.dummy.source_monitor import DummySourceMonitorAdapter
from app.core.domain.source import ChangeSet, FileChange
from app.core.services.source_monitor_service import MAX_FILES_PER_CYCLE, SourceMonitorService


@given(st.integers(min_value=0, max_value=50))
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_batch_size_invariant(file_count: int) -> None:
    session = AsyncMock()
    source_id = uuid.uuid4()
    source = MagicMock()
    source.id = source_id
    source.status = "active"
    source.last_sync_token = None
    source.source_type = "drive"
    source.config = {"folder_id": "f1", "folder_name": "Test", "polling_interval_minutes": 15}
    source.error_count = 0
    source.user_id = uuid.uuid4()
    source.last_sync_count = 0
    source.last_sync_at = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = source
    session.execute.return_value = mock_result
    session.commit = AsyncMock()

    files = [
        FileChange(file_id=f"f{i}", filename=f"d{i}.pdf", mime_type="application/pdf", modified_at=datetime.now(UTC))
        for i in range(file_count)
    ]
    monitor = DummySourceMonitorAdapter()
    monitor.changesets.append(ChangeSet(new_files=files, new_sync_token="t"))

    service = SourceMonitorService(session, monitor)
    result = await service.poll_source(source_id)
    assert len(result.new_files) <= MAX_FILES_PER_CYCLE


@given(st.integers(min_value=5, max_value=1440))
@settings(max_examples=10)
def test_polling_interval_valid_range(minutes: int) -> None:
    from app.core.domain.source import DriveSourceConfig
    cfg = DriveSourceConfig(folder_id="f", folder_name="F", polling_interval_minutes=minutes)
    assert 5 <= cfg.polling_interval_minutes <= 1440
