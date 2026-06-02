"""CrossDocGraph — LangGraph pipeline for cross-document correlation.

Flow: input → entity extraction → correlation detection → conflict detection → persistence
Risk score: 1 (internal write)

Requirements: 7
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.agent.nodes.correlation_detector_node import CorrelationDetectorNode
from app.core.domain.correlation import DocumentCorrelation
from app.core.ports.llm import LLMProviderPort
from app.core.services.cross_document_service import CrossDocumentService

logger = structlog.get_logger()


class CrossDocGraph:
    """Detect and persist cross-document correlations."""

    RISK_SCORE = 1

    def __init__(
        self,
        llm: LLMProviderPort,
        cross_doc_service: CrossDocumentService | None = None,
    ) -> None:
        self._detector = CorrelationDetectorNode(llm)
        self._cross_doc_service = cross_doc_service

    async def run(
        self,
        user_id: str,
        source_document_id: str,
        source_text: str,
        candidate_documents: list[dict[str, Any]],
        persist: bool = True,
    ) -> dict[str, Any]:
        """Execute cross-document correlation pipeline."""
        raw_correlations = await self._detector.run(
            source_document_id=source_document_id,
            source_text=source_text,
            candidate_documents=candidate_documents,
        )

        conflicts = [c for c in raw_correlations if c.get("correlation_type") == "in_conflitto_con"]
        stored = []

        if persist and self._cross_doc_service and raw_correlations:
            user_uuid = uuid.UUID(user_id)
            domain_correlations = []
            for corr in raw_correlations:
                domain_correlations.append(
                    DocumentCorrelation(
                        id=uuid.uuid4(),
                        source_document_id=uuid.UUID(source_document_id),
                        target_document_id=uuid.UUID(corr["target_document_id"]),
                        correlation_type=corr["correlation_type"],  # type: ignore[arg-type]
                        confidence_score=corr.get("confidence_score", 0.5),
                        source_passage=corr.get("source_passage"),
                        target_passage=corr.get("target_passage"),
                        source_page=corr.get("source_page"),
                        target_page=corr.get("target_page"),
                    )
                )
            stored_results = await self._cross_doc_service.store_correlations_batch(
                user_id=user_uuid,
                correlations=domain_correlations,
            )
            stored = [c.model_dump(mode="json") for c in stored_results]

        logger.info(
            "cross_doc_graph_completed",
            source_document_id=source_document_id,
            correlations_found=len(raw_correlations),
            conflicts=len(conflicts),
            persisted=len(stored),
        )

        return {
            "source_document_id": source_document_id,
            "risk_score": self.RISK_SCORE,
            "correlations": raw_correlations,
            "conflicts": conflicts,
            "stored": stored,
        }
