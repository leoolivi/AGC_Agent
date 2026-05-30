"""
VectorStorePort — Protocol for vector store backends.

Implementations: PgvectorAdapter (app/adapters/vector/).
Wiring: app/api/deps.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class VectorSearchResult:
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class VectorStorePort(Protocol):
    async def upsert(
        self,
        document_id: str,
        chunks: list[str],
        metadata: list[dict],
    ) -> bool: ...

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
    ) -> list[VectorSearchResult]: ...

    async def delete(self, document_id: str) -> bool: ...
