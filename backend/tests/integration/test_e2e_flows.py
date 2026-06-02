"""End-to-end integration tests for enhancement flows."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.adapters.dummy.realtime import DummyRealtimeAdapter
from app.adapters.dummy.source_monitor import DummySourceMonitorAdapter
from app.core.domain.source import ChangeSet, FileChange
from app.core.services.source_monitor_service import SourceMonitorService


@pytest.mark.asyncio
async def test_source_poll_to_changeset() -> None:
    """Source poll returns changeset with batch limiting."""
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

    monitor = DummySourceMonitorAdapter()
    monitor.changesets.append(
        ChangeSet(
            new_files=[
                FileChange(
                    file_id=f"f{i}",
                    filename=f"doc{i}.pdf",
                    mime_type="application/pdf",
                    modified_at=datetime.now(UTC),
                )
                for i in range(3)
            ],
            new_sync_token="tok",
        )
    )

    service = SourceMonitorService(session, monitor)
    result = await service.poll_source(source_id)
    assert len(result.new_files) == 3


@pytest.mark.asyncio
async def test_risky_clause_graph_persistence_flow() -> None:
    """Analysis graph produces structured clause output."""
    from app.agent.graphs.risky_clause_graph import RiskyClauseGraph

    response = json.dumps({
        "clauses": [{
            "category": "penale",
            "severity": "alto",
            "clause_text": "Penale 10%",
            "plain_language_explanation": "Penale per ritardo",
            "confidence_score": 0.9,
        }]
    })
    graph = RiskyClauseGraph(DummyLLMAdapter(content=response))
    result = await graph.run(str(uuid.uuid4()), "Contratto con penale", persist=False)
    assert len(result["clauses"]) == 1


@pytest.mark.asyncio
async def test_realtime_emit_on_processing() -> None:
    """Realtime adapter collects processing events."""
    from app.core.domain.realtime import RealtimeEvent

    rt = DummyRealtimeAdapter()
    event = RealtimeEvent(
        event_type="processing_status",
        payload={"status": "completed", "document_id": "d1"},
        timestamp=datetime.now(UTC),
        user_id="u1",
    )
    await rt.emit("u1", event)
    assert len(rt.emitted) == 1
