"""Tests for chunking invariants and VectorStore (using DummyVectorAdapter)."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.adapters.dummy.vector import DummyVectorAdapter
from app.adapters.vector.chunking import chunk_text


class TestChunking:
    def test_short_text_single_chunk(self) -> None:
        text = " ".join(["word"] * 100)
        chunks = chunk_text(text)
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self) -> None:
        text = " ".join(["word"] * 1000)
        chunks = chunk_text(text, max_tokens=512, overlap=64)
        assert len(chunks) > 1

    def test_empty_text(self) -> None:
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    @given(
        word_count=st.integers(min_value=64, max_value=2000),
    )
    @settings(max_examples=100)
    def test_chunk_size_invariants(self, word_count: int) -> None:
        """Every chunk must have at most max_tokens words."""
        text = " ".join(["w"] * word_count)
        chunks = chunk_text(text, max_tokens=512, min_tokens=64, overlap=64)
        for chunk in chunks:
            words = chunk.split()
            assert len(words) <= 512

    def test_overlap_present(self) -> None:
        """Consecutive chunks should share overlap words."""
        text = " ".join([f"w{i}" for i in range(1024)])
        chunks = chunk_text(text, max_tokens=512, overlap=64)
        if len(chunks) >= 2:
            words_0 = set(chunks[0].split()[-64:])
            words_1 = set(chunks[1].split()[:64])
            assert len(words_0 & words_1) == 64


class TestVectorStore:
    @pytest.mark.asyncio
    async def test_upsert_and_search(self) -> None:
        store = DummyVectorAdapter()
        ok = await store.upsert("doc-1", ["hello world", "foo bar"], [{"user_id": "u1"}, {"user_id": "u1"}])
        assert ok is True
        results = await store.search("hello", "u1")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_filters_by_user(self) -> None:
        store = DummyVectorAdapter()
        await store.upsert("doc-1", ["secret data"], [{"user_id": "u1"}])
        results = await store.search("secret", "u2")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        store = DummyVectorAdapter()
        await store.upsert("doc-1", ["text"], [{"user_id": "u1"}])
        assert await store.delete("doc-1") is True
        results = await store.search("text", "u1")
        assert results == []
