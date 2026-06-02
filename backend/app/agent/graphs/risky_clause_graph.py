"""RiskyClauseGraph — LangGraph pipeline for contract clause analysis.

Flow: input → clause detection → structured output → persistence
Risk score: 0 (read-only analysis)

Requirements: 5
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.agent.nodes.clause_detector_node import ClauseDetectorNode
from app.core.ports.llm import LLMProviderPort
from app.core.services.risky_clause_service import RiskyClauseService

logger = structlog.get_logger()


class RiskyClauseGraph:
    """Analyze contracts for risky clauses with structured output."""

    RISK_SCORE = 0

    def __init__(
        self,
        llm: LLMProviderPort,
        clause_service: RiskyClauseService | None = None,
    ) -> None:
        self._detector = ClauseDetectorNode(llm)
        self._clause_service = clause_service

    async def run(
        self,
        document_id: str,
        document_text: str,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Execute clause detection pipeline."""
        clauses = await self._detector.run(document_text, document_id)

        stored = []
        if persist and self._clause_service and clauses:
            doc_uuid = uuid.UUID(document_id)
            for clause in clauses:
                stored_clause = await self._clause_service.store_clause(
                    document_id=doc_uuid,
                    category=clause["category"],  # type: ignore[arg-type]
                    severity=clause["severity"],  # type: ignore[arg-type]
                    clause_text=clause.get("clause_text", ""),
                    plain_language_explanation=clause.get("plain_language_explanation", ""),
                    confidence_score=clause.get("confidence_score", 0.5),
                    page_number=clause.get("page_number"),
                    paragraph_ref=clause.get("paragraph_ref"),
                )
                stored.append(stored_clause.model_dump(mode="json"))

        logger.info(
            "risky_clause_graph_completed",
            document_id=document_id,
            clauses_found=len(clauses),
            persisted=len(stored),
        )

        return {
            "document_id": document_id,
            "risk_score": self.RISK_SCORE,
            "clauses": clauses,
            "stored": stored,
        }
