"""
DummyVectorAdapter — in-memory implementation of VectorStorePort.

Stores chunks in a plain dict. Search returns all stored chunks for the
given user_id ordered by insertion (no real cosine similarity).
No external dependencies. Safe to use in unit tests.
"""
from __future__ import annotations

import uuid

from app.core.ports.vector import VectorSearchResult, VectorStorePort


class DummyVectorAdapter:
    """In-memory VectorStorePort implementation for testing."""

    def __init__(self) -> None:
        # document_id → list of (chunk_id, text, metadata, user_id)
        self._store: dict[str, list[tuple[str, str, dict, str]]] = {}

    async def upsert(
        self,
        document_id: str,
        chunks: list[str],
        metadata: list[dict],
    ) -> bool:
        if len(chunks) != len(metadata):
            return False
        entries = [
            (str(uuid.uuid4()), text, meta, meta.get("user_id", ""))
            for text, meta in zip(chunks, metadata)
        ]
        self._store[document_id] = entries
        return True

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
    ) -> list[VectorSearchResult]:
        results: list[VectorSearchResult] = []
        for document_id, entries in self._store.items():
            for chunk_id, text, meta, stored_user_id in entries:
                if stored_user_id != user_id:
                    continue
                # Dummy score: 1.0 if query appears in text, else 0.5
                score = 1.0 if query.lower() in text.lower() else 0.5
                results.append(
                    VectorSearchResult(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=text,
                        score=score,
                        metadata=meta,
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def delete(self, document_id: str) -> bool:
        if document_id not in self._store:
            return False
        del self._store[document_id]
        return True


# Verify structural compatibility at import time.
def _assert_protocol() -> None:
    _: VectorStorePort = DummyVectorAdapter()  # type: ignore[assignment]


_assert_protocol()
