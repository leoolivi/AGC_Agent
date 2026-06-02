"""Post-ingest analysis graph triggers."""
from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.agent.graphs.calendar_relevance_graph import CalendarRelevanceGraph
from app.agent.graphs.cross_doc_graph import CrossDocGraph
from app.agent.graphs.risky_clause_graph import RiskyClauseGraph
from app.api.deps import get_llm
from app.core.services.cross_document_service import CrossDocumentService
from app.core.services.risky_clause_service import RiskyClauseService
from app.db.session import build_session_factory
from app.config import settings
from sqlalchemy import select
from app.db.models import Document

logger = structlog.get_logger()


async def trigger_post_ingest_analysis(
    user_id: str,
    document_id: str,
    document_type: str,
    document_text: str = "",
) -> dict[str, Any]:
    """Trigger analysis graphs after document ingestion."""
    results: dict[str, Any] = {}
    llm = get_llm()
    factory = build_session_factory(settings.database_url)

    async with factory() as session:
        if document_type == "contratto" and document_text:
            clause_service = RiskyClauseService(session)
            graph = RiskyClauseGraph(llm, clause_service)
            results["risky_clauses"] = await graph.run(document_id, document_text, persist=True)

        cross_service = CrossDocumentService(session)
        candidates_result = await session.execute(
            select(Document)
            .where(Document.user_id == uuid.UUID(user_id))
            .where(Document.id != uuid.UUID(document_id))
            .limit(20)
        )
        candidates = [
            {"id": str(d.id), "filename": d.filename, "document_type": d.document_type, "text": ""}
            for d in candidates_result.scalars().all()
        ]
        if document_text:
            cross_graph = CrossDocGraph(llm, cross_service)
            results["correlations"] = await cross_graph.run(
                user_id, document_id, document_text, candidates, persist=True
            )

    logger.info("post_ingest_analysis_complete", document_id=document_id, graphs=list(results.keys()))
    return results


async def trigger_calendar_analysis(event: dict[str, Any]) -> dict[str, Any]:
    """Classify calendar event relevance."""
    llm = get_llm()
    graph = CalendarRelevanceGraph(llm)
    return await graph.run(event)
