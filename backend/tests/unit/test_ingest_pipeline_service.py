"""Unit tests for IngestPipelineService."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.adapters.dummy.parser import DummyParserAdapter
from app.adapters.dummy.realtime import DummyRealtimeAdapter
from app.adapters.dummy.source_monitor import DummySourceMonitorAdapter
from app.adapters.dummy.vector import DummyVectorAdapter
from app.core.domain.source import FileChange
from app.core.services.document_pipeline import DocumentPipeline
from app.core.services.ingest_pipeline_service import IngestPipelineService


@pytest.fixture
def ingest_service() -> IngestPipelineService:
    monitor = DummySourceMonitorAdapter()
    monitor.seed_file("file-1", b"%PDF-1.4 fake content")
    llm = DummyLLMAdapter(content='{"document_type": "fattura", "confidence": 0.92}')
    parser = DummyParserAdapter(text="Fattura test", confidence=0.90)
    pipeline = DocumentPipeline(parser=parser, llm=llm, vector_store=DummyVectorAdapter())
    realtime = DummyRealtimeAdapter()
    return IngestPipelineService(monitor, pipeline, realtime)


@pytest.fixture
def file_change() -> FileChange:
    return FileChange(
        file_id="file-1",
        filename="fattura.pdf",
        mime_type="application/pdf",
        modified_at=datetime.now(UTC),
    )


class TestIngestPipelineService:
    @pytest.mark.asyncio
    async def test_document_creation_with_source_metadata(
        self, ingest_service: IngestPipelineService, file_change: FileChange
    ) -> None:
        user_id = str(uuid.uuid4())
        doc = await ingest_service.ingest_file(file_change, "drive", user_id)

        assert doc is not None
        assert doc.source == "drive"
        assert doc.source_ref_id == "file-1"
        assert doc.filename == "fattura.pdf"

    @pytest.mark.asyncio
    async def test_format_filtering_skips_unsupported(
        self, ingest_service: IngestPipelineService
    ) -> None:
        unsupported = FileChange(
            file_id="file-2",
            filename="image.png",
            mime_type="image/png",
            modified_at=datetime.now(UTC),
        )
        result = await ingest_service.ingest_file(unsupported, "drive", str(uuid.uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_status_emission(
        self, ingest_service: IngestPipelineService, file_change: FileChange
    ) -> None:
        user_id = str(uuid.uuid4())
        realtime = ingest_service._realtime  # type: ignore[attr-defined]
        assert isinstance(realtime, DummyRealtimeAdapter)

        await ingest_service.ingest_file(file_change, "gmail", user_id)

        assert len(realtime.emitted) >= 2
        event_types = [e[1].event_type for e in realtime.emitted]
        assert all(t == "processing_status" for t in event_types)
        statuses = [e[1].payload.get("status") for e in realtime.emitted]
        assert "ingesting" in statuses
        assert "parsing" in statuses or "completed" in statuses
