"""Unit tests for Protocol dummy implementations.

Verifies that every dummy adapter:
1. Implements the Protocol interface correctly (runtime_checkable)
2. Is instantiable without external dependencies
3. Returns expected types from all methods
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

from app.adapters.dummy.calendar import DummyCalendarAdapter
from app.adapters.dummy.email import DummyEmailAdapter
from app.adapters.dummy.llm import DummyLLMAdapter
from app.adapters.dummy.notifier import DummyNotifierAdapter
from app.adapters.dummy.parser import DummyParserAdapter
from app.adapters.dummy.storage import DummyStorageAdapter
from app.adapters.dummy.vector import DummyVectorAdapter
from app.core.ports.calendar import CalendarEvent, CalendarPort
from app.core.ports.email import EmailMessage, EmailSenderPort
from app.core.ports.llm import LLMProviderPort, LLMResponse
from app.core.ports.notifier import NotifierPort
from app.core.ports.parser import DocumentParserPort, ParsedDocument
from app.core.ports.storage import FileMetadata, FileStoragePort
from app.core.ports.vector import VectorSearchResult, VectorStorePort


class TestDummyStorageAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyStorageAdapter(), FileStoragePort)

    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        adapter = DummyStorageAdapter()
        meta = await adapter.save(io.BytesIO(b"hello"), "test.pdf", "user1", "application/pdf")
        assert isinstance(meta, FileMetadata)
        assert meta.filename == "test.pdf"
        assert meta.user_id == "user1"
        data = await adapter.get(meta.file_id)
        assert data == b"hello"

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        adapter = DummyStorageAdapter()
        meta = await adapter.save(io.BytesIO(b"x"), "f.txt", "u1", "text/plain")
        assert await adapter.delete(meta.file_id) is True
        assert await adapter.delete(meta.file_id) is False

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        adapter = DummyStorageAdapter()
        await adapter.save(io.BytesIO(b"a"), "a.txt", "u1", "text/plain")
        await adapter.save(io.BytesIO(b"b"), "b.txt", "u2", "text/plain")
        results = await adapter.list("u1")
        assert len(results) == 1
        assert results[0].user_id == "u1"


class TestDummyLLMAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyLLMAdapter(), LLMProviderPort)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        adapter = DummyLLMAdapter(content="test output")
        resp = await adapter.generate("prompt", "system")
        assert isinstance(resp, LLMResponse)
        assert resp.content == "test output"
        assert resp.model == DummyLLMAdapter.DEFAULT_MODEL

    @pytest.mark.asyncio
    async def test_stream(self) -> None:
        adapter = DummyLLMAdapter(content="hello world")
        gen = await adapter.stream("prompt", "system")
        tokens = [t async for t in gen]
        assert tokens == ["hello", "world"]


class TestDummyParserAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyParserAdapter(), DocumentParserPort)

    def test_can_parse(self) -> None:
        adapter = DummyParserAdapter(supported_types=("application/pdf",))
        assert adapter.can_parse("application/pdf", "doc.pdf") is True
        assert adapter.can_parse("text/csv", "data.csv") is False

    @pytest.mark.asyncio
    async def test_parse(self) -> None:
        adapter = DummyParserAdapter(text="parsed content", confidence=0.95)
        result = await adapter.parse(b"raw bytes", "doc.pdf")
        assert isinstance(result, ParsedDocument)
        assert result.text == "parsed content"
        assert result.confidence == 0.95


class TestDummyEmailAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyEmailAdapter(), EmailSenderPort)

    @pytest.mark.asyncio
    async def test_send(self) -> None:
        adapter = DummyEmailAdapter()
        msg = EmailMessage(
            to=["a@b.com"], subject="Hi", body_html="<p>Hi</p>", body_text="Hi"
        )
        assert await adapter.send(msg) is True
        assert adapter.sent_messages == [msg]

    @pytest.mark.asyncio
    async def test_send_draft(self) -> None:
        adapter = DummyEmailAdapter()
        assert await adapter.send_draft("draft-1") is True
        assert adapter.sent_draft_ids == ["draft-1"]


class TestDummyVectorAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyVectorAdapter(), VectorStorePort)

    @pytest.mark.asyncio
    async def test_upsert_and_search(self) -> None:
        adapter = DummyVectorAdapter()
        ok = await adapter.upsert(
            "doc1", ["chunk with hello"], [{"user_id": "u1"}]
        )
        assert ok is True
        results = await adapter.search("hello", "u1", top_k=5)
        assert len(results) == 1
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].score == 1.0

    @pytest.mark.asyncio
    async def test_search_filters_by_user(self) -> None:
        adapter = DummyVectorAdapter()
        await adapter.upsert("doc1", ["text"], [{"user_id": "u1"}])
        results = await adapter.search("text", "u2")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        adapter = DummyVectorAdapter()
        await adapter.upsert("doc1", ["text"], [{"user_id": "u1"}])
        assert await adapter.delete("doc1") is True
        assert await adapter.delete("doc1") is False


class TestDummyCalendarAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyCalendarAdapter(), CalendarPort)

    @pytest.mark.asyncio
    async def test_create_and_delete_event(self) -> None:
        adapter = DummyCalendarAdapter()
        event = CalendarEvent(
            title="Meeting",
            due_datetime=datetime(2026, 6, 1, 10, 0),
            description="Test",
        )
        event_id = await adapter.create_event(event, "u1")
        assert isinstance(event_id, str)
        assert await adapter.delete_event(event_id, "u1") is True
        assert await adapter.delete_event(event_id, "u1") is False


class TestDummyNotifierAdapter:
    def test_implements_protocol(self) -> None:
        assert isinstance(DummyNotifierAdapter(), NotifierPort)

    @pytest.mark.asyncio
    async def test_send_inapp(self) -> None:
        adapter = DummyNotifierAdapter()
        assert await adapter.send_inapp("u1", "Title", "Body", "info") is True
        assert len(adapter.inapp_notifications) == 1

    @pytest.mark.asyncio
    async def test_send_email_notification(self) -> None:
        adapter = DummyNotifierAdapter()
        assert await adapter.send_email_notification("u1", "Subj", "Body") is True
        assert len(adapter.email_notifications) == 1
