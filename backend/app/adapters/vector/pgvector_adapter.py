"""PgvectorAdapter — vector store via PostgreSQL pgvector extension."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.vector.chunking import chunk_text
from app.core.ports.vector import VectorSearchResult, VectorStorePort

logger = structlog.get_logger()


class PgvectorAdapter(VectorStorePort):
    """VectorStore implementation using pgvector. Manages embedding generation internally."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_fn=None,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_fn = embedding_fn  # async fn(text) -> list[float]

    async def _get_embedding(self, text_content: str) -> list[float]:
        """Generate embedding via configured function or return zeros for testing."""
        if self._embedding_fn:
            return await self._embedding_fn(text_content)
        # Fallback: zero vector (for testing without OpenAI)
        return [0.0] * 1536

    async def upsert(
        self, document_id: str, chunks: list[str], metadata: list[dict]
    ) -> bool:
        try:
            async with self._session_factory() as session:
                # Delete existing chunks for this document
                await session.execute(
                    text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
                    {"doc_id": document_id},
                )
                # Insert new chunks
                for i, (chunk, meta) in enumerate(zip(chunks, metadata)):
                    chunk_id = str(uuid.uuid4())
                    user_id = meta.get("user_id", "")
                    embedding = await self._get_embedding(chunk)
                    await session.execute(
                        text(
                            "INSERT INTO document_chunks (id, document_id, user_id, chunk_index, content, metadata, embedding) "
                            "VALUES (:id, :doc_id, :user_id, :idx, :content, :meta::jsonb, :embedding::vector)"
                        ),
                        {
                            "id": chunk_id,
                            "doc_id": document_id,
                            "user_id": user_id,
                            "idx": i,
                            "content": chunk,
                            "meta": "{}",
                            "embedding": str(embedding),
                        },
                    )
                await session.commit()
            return True
        except Exception as e:
            logger.error("pgvector_upsert_failed", document_id=document_id, error=str(e))
            return False

    async def search(
        self, query: str, user_id: str, top_k: int = 10
    ) -> list[VectorSearchResult]:
        try:
            query_embedding = await self._get_embedding(query)
            async with self._session_factory() as session:
                result = await session.execute(
                    text(
                        "SELECT id, document_id, content, "
                        "1 - (embedding <=> :embedding::vector) as score "
                        "FROM document_chunks "
                        "WHERE user_id = :user_id "
                        "ORDER BY embedding <=> :embedding::vector "
                        "LIMIT :top_k"
                    ),
                    {
                        "embedding": str(query_embedding),
                        "user_id": user_id,
                        "top_k": top_k,
                    },
                )
                rows = result.fetchall()
            return [
                VectorSearchResult(
                    chunk_id=str(row[0]),
                    document_id=str(row[1]),
                    text=row[2],
                    score=float(row[3]),
                )
                for row in rows
            ]
        except Exception as e:
            logger.error("pgvector_search_failed", error=str(e))
            return []

    async def delete(self, document_id: str) -> bool:
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
                    {"doc_id": document_id},
                )
                await session.commit()
                return result.rowcount > 0  # type: ignore[union-attr]
        except Exception as e:
            logger.error("pgvector_delete_failed", document_id=document_id, error=str(e))
            return False
