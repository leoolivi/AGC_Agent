"""CrossDocumentService — Correlation storage, retrieval, and conflict detection.

This service manages cross-document correlations with:
- Correlation storage and retrieval by document
- Confidence-based visibility thresholds:
  - >= 0.85: "certain" (based on explicit references)
  - 0.60-0.85: "probable" (based on semantic inference)
  - < 0.60: hidden (not displayed)
- Conflict detection triggering AgentInboxItem with urgency "today"

Requirements: 7
Properties: 14, 15, 16
"""

from __future__ import annotations

import uuid
from typing import Literal

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.correlation import DocumentCorrelation as DocumentCorrelationDomain
from app.core.domain.inbox import AgentInboxItem
from app.db.models import AgentInbox
from app.db.models import DocumentCorrelation as DocumentCorrelationORM

logger = structlog.get_logger()

# Confidence thresholds for visibility classification (Property 16)
CONFIDENCE_THRESHOLD_CERTAIN = 0.85
CONFIDENCE_THRESHOLD_PROBABLE = 0.60


class CrossDocumentService:
    """Service for managing cross-document correlations and conflict detection."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def store_correlation(
        self,
        user_id: uuid.UUID,
        source_document_id: uuid.UUID,
        target_document_id: uuid.UUID,
        correlation_type: Literal["derivato_da", "versione_di", "allegato_di", "in_conflitto_con"],
        confidence_score: float,
        source_passage: str | None = None,
        target_passage: str | None = None,
        source_page: int | None = None,
        target_page: int | None = None,
    ) -> DocumentCorrelationDomain:
        """Store a newly detected document correlation.

        This method validates structural requirements via Pydantic domain model:
        - source and target documents must differ (Property 14)
        - confidence_score must be in [0.0, 1.0]
        - correlation_type must be valid

        If correlation_type is "in_conflitto_con", this method will create an
        AgentInboxItem with urgency="today" (Property 15).

        Args:
            user_id: The user who owns both documents.
            source_document_id: The source document in the correlation.
            target_document_id: The target document in the correlation.
            correlation_type: Type of correlation (derivato_da, versione_di,
                             allegato_di, in_conflitto_con).
            confidence_score: Confidence score (0.0-1.0).
            source_passage: Optional text from source doc justifying correlation.
            target_passage: Optional text from target doc justifying correlation.
            source_page: Optional page number in source document.
            target_page: Optional page number in target document.

        Returns:
            The created DocumentCorrelation domain model.

        Raises:
            ValueError: If source and target documents are the same, or if
                       confidence_score is out of range (validated by Pydantic).
        """
        correlation_id = uuid.uuid4()

        # Create domain model first to trigger Pydantic validation (Property 14)
        domain_correlation = DocumentCorrelationDomain(
            id=correlation_id,
            source_document_id=source_document_id,
            target_document_id=target_document_id,
            correlation_type=correlation_type,
            confidence_score=confidence_score,
            source_passage=source_passage,
            target_passage=target_passage,
            source_page=source_page,
            target_page=target_page,
        )

        # Create ORM model
        orm_correlation = DocumentCorrelationORM(
            id=correlation_id,
            user_id=user_id,
            source_document_id=source_document_id,
            target_document_id=target_document_id,
            correlation_type=correlation_type,
            confidence_score=confidence_score,
            source_passage=source_passage,
            target_passage=target_passage,
            source_page=source_page,
            target_page=target_page,
        )

        self._session.add(orm_correlation)
        await self._session.commit()
        await self._session.refresh(orm_correlation)

        logger.info(
            "correlation_stored",
            correlation_id=str(correlation_id),
            source_document_id=str(source_document_id),
            target_document_id=str(target_document_id),
            correlation_type=correlation_type,
            confidence_score=confidence_score,
        )

        # If this is a conflict, create an urgent inbox item (Property 15)
        if correlation_type == "in_conflitto_con":
            await self._create_conflict_inbox_item(
                user_id=user_id,
                correlation=domain_correlation,
            )

        return domain_correlation

    async def store_correlations_batch(
        self,
        user_id: uuid.UUID,
        correlations: list[DocumentCorrelationDomain],
    ) -> list[DocumentCorrelationDomain]:
        """Store multiple correlations in a single transaction.

        Useful when the CrossDocGraph detects multiple correlations in one analysis.

        Args:
            user_id: The user who owns the documents.
            correlations: List of DocumentCorrelation domain models to store.

        Returns:
            List of stored DocumentCorrelation domain models.

        Raises:
            ValueError: If any correlation fails Pydantic validation.
        """
        orm_correlations = []
        conflict_correlations = []

        for correlation in correlations:
            orm_correlation = DocumentCorrelationORM(
                id=correlation.id,
                user_id=user_id,
                source_document_id=correlation.source_document_id,
                target_document_id=correlation.target_document_id,
                correlation_type=correlation.correlation_type,
                confidence_score=correlation.confidence_score,
                source_passage=correlation.source_passage,
                target_passage=correlation.target_passage,
                source_page=correlation.source_page,
                target_page=correlation.target_page,
            )
            orm_correlations.append(orm_correlation)

            # Track conflicts for inbox item creation
            if correlation.correlation_type == "in_conflitto_con":
                conflict_correlations.append(correlation)

        self._session.add_all(orm_correlations)
        await self._session.commit()

        # Create inbox items for all conflicts (Property 15)
        for conflict in conflict_correlations:
            await self._create_conflict_inbox_item(
                user_id=user_id,
                correlation=conflict,
            )

        logger.info(
            "correlations_batch_stored",
            user_id=str(user_id),
            count=len(correlations),
            conflicts=len(conflict_correlations),
        )

        return correlations

    async def get_correlations_by_document(
        self,
        document_id: uuid.UUID,
        min_confidence: float | None = None,
        correlation_type: str | None = None,
        include_hidden: bool = False,
    ) -> list[DocumentCorrelationDomain]:
        """Retrieve all correlations for a document with optional filtering.

        By default, only correlations with confidence >= 0.60 are returned
        (Property 16). Set include_hidden=True to retrieve all correlations.

        Args:
            document_id: The document ID (as source or target).
            min_confidence: Optional minimum confidence threshold.
            correlation_type: Optional correlation type filter.
            include_hidden: If False (default), hide correlations with
                           confidence < 0.60.

        Returns:
            List of DocumentCorrelation domain models.
        """
        # Find correlations where document is either source or target
        query = select(DocumentCorrelationORM).where(
            or_(
                DocumentCorrelationORM.source_document_id == document_id,
                DocumentCorrelationORM.target_document_id == document_id,
            )
        )

        # Apply confidence threshold (Property 16)
        if not include_hidden:
            effective_min_confidence = max(
                min_confidence or 0.0,
                CONFIDENCE_THRESHOLD_PROBABLE,
            )
            query = query.where(DocumentCorrelationORM.confidence_score >= effective_min_confidence)
        elif min_confidence is not None:
            query = query.where(DocumentCorrelationORM.confidence_score >= min_confidence)

        if correlation_type:
            query = query.where(DocumentCorrelationORM.correlation_type == correlation_type)

        # Order by confidence descending
        query = query.order_by(DocumentCorrelationORM.confidence_score.desc())

        result = await self._session.execute(query)
        orm_correlations = result.scalars().all()

        domain_correlations = [self._to_domain(c) for c in orm_correlations]

        logger.debug(
            "correlations_retrieved",
            document_id=str(document_id),
            count=len(domain_correlations),
            min_confidence=min_confidence,
            correlation_type=correlation_type,
            include_hidden=include_hidden,
        )

        return domain_correlations

    async def get_correlation_by_id(
        self,
        correlation_id: uuid.UUID,
    ) -> DocumentCorrelationDomain | None:
        """Retrieve a single correlation by ID.

        Args:
            correlation_id: The correlation ID.

        Returns:
            DocumentCorrelation domain model if found, None otherwise.
        """
        result = await self._session.execute(
            select(DocumentCorrelationORM).where(DocumentCorrelationORM.id == correlation_id)
        )
        orm_correlation = result.scalar_one_or_none()
        return self._to_domain(orm_correlation) if orm_correlation else None

    async def get_certain_correlations(
        self,
        document_id: uuid.UUID,
    ) -> list[DocumentCorrelationDomain]:
        """Retrieve correlations with confidence >= 0.85 (certain).

        These correlations are based on explicit references in the documents.

        Args:
            document_id: The document ID.

        Returns:
            List of certain DocumentCorrelation domain models.
        """
        return await self.get_correlations_by_document(
            document_id=document_id,
            min_confidence=CONFIDENCE_THRESHOLD_CERTAIN,
        )

    async def get_probable_correlations(
        self,
        document_id: uuid.UUID,
    ) -> list[DocumentCorrelationDomain]:
        """Retrieve correlations with confidence in [0.60, 0.85) (probable).

        These correlations are based on semantic inference.

        Args:
            document_id: The document ID.

        Returns:
            List of probable DocumentCorrelation domain models.
        """
        query = select(DocumentCorrelationORM).where(
            or_(
                DocumentCorrelationORM.source_document_id == document_id,
                DocumentCorrelationORM.target_document_id == document_id,
            ),
            DocumentCorrelationORM.confidence_score >= CONFIDENCE_THRESHOLD_PROBABLE,
            DocumentCorrelationORM.confidence_score < CONFIDENCE_THRESHOLD_CERTAIN,
        )

        result = await self._session.execute(query)
        orm_correlations = result.scalars().all()

        return [self._to_domain(c) for c in orm_correlations]

    async def get_conflicts(
        self,
        document_id: uuid.UUID,
    ) -> list[DocumentCorrelationDomain]:
        """Retrieve all conflict correlations for a document.

        Args:
            document_id: The document ID.

        Returns:
            List of conflict DocumentCorrelation domain models.
        """
        return await self.get_correlations_by_document(
            document_id=document_id,
            correlation_type="in_conflitto_con",
        )

    async def get_correlations_by_type(
        self,
        document_id: uuid.UUID,
        correlation_type: Literal["derivato_da", "versione_di", "allegato_di", "in_conflitto_con"],
    ) -> list[DocumentCorrelationDomain]:
        """Retrieve correlations of a specific type for a document.

        Args:
            document_id: The document ID.
            correlation_type: The correlation type to filter by.

        Returns:
            List of DocumentCorrelation domain models.
        """
        return await self.get_correlations_by_document(
            document_id=document_id,
            correlation_type=correlation_type,
        )

    async def delete_correlations_by_document(
        self,
        document_id: uuid.UUID,
    ) -> int:
        """Delete all correlations involving a document.

        This is typically called when a document is deleted.

        Args:
            document_id: The document ID.

        Returns:
            Number of correlations deleted.
        """
        result = await self._session.execute(
            select(DocumentCorrelationORM).where(
                or_(
                    DocumentCorrelationORM.source_document_id == document_id,
                    DocumentCorrelationORM.target_document_id == document_id,
                )
            )
        )
        orm_correlations = result.scalars().all()
        count = len(orm_correlations)

        for correlation in orm_correlations:
            await self._session.delete(correlation)

        await self._session.commit()

        logger.info(
            "correlations_deleted",
            document_id=str(document_id),
            count=count,
        )

        return count

    async def count_correlations_by_document(
        self,
        document_id: uuid.UUID,
    ) -> int:
        """Count total correlations for a document (visible only).

        Args:
            document_id: The document ID.

        Returns:
            Total number of visible correlations (confidence >= 0.60).
        """
        correlations = await self.get_correlations_by_document(
            document_id=document_id,
            include_hidden=False,
        )
        return len(correlations)

    async def count_by_type(
        self,
        document_id: uuid.UUID,
    ) -> dict[str, int]:
        """Count correlations by type for a document.

        Args:
            document_id: The document ID.

        Returns:
            Dictionary mapping correlation type to count.
        """
        correlations = await self.get_correlations_by_document(
            document_id=document_id,
            include_hidden=False,
        )

        counts = {
            "derivato_da": 0,
            "versione_di": 0,
            "allegato_di": 0,
            "in_conflitto_con": 0,
        }

        for correlation in correlations:
            counts[correlation.correlation_type] += 1

        return counts

    def classify_confidence(
        self,
        correlation: DocumentCorrelationDomain,
    ) -> Literal["certain", "probable", "hidden"]:
        """Classify a correlation's confidence level for UI display.

        This helper method implements Property 16 for UI components.

        Args:
            correlation: The DocumentCorrelation domain model.

        Returns:
            "certain" if confidence >= 0.85,
            "probable" if 0.60 <= confidence < 0.85,
            "hidden" if confidence < 0.60.
        """
        if correlation.confidence_score >= CONFIDENCE_THRESHOLD_CERTAIN:
            return "certain"
        elif correlation.confidence_score >= CONFIDENCE_THRESHOLD_PROBABLE:
            return "probable"
        else:
            return "hidden"

    async def _create_conflict_inbox_item(
        self,
        user_id: uuid.UUID,
        correlation: DocumentCorrelationDomain,
    ) -> AgentInboxItem:
        """Create an AgentInboxItem for a detected conflict.

        This implements Property 15: conflicts trigger urgent inbox items.

        Args:
            user_id: The user who owns the documents.
            correlation: The conflict correlation.

        Returns:
            The created AgentInboxItem domain model.
        """
        inbox_item_id = uuid.uuid4()

        # Build conflict description
        conflict_description = self._build_conflict_description(correlation)

        # Build suggested actions
        suggested_actions = [
            {
                "id": "review_documents",
                "label": "Rivedi entrambi i documenti",
                "verb": "review",
                "risk_level": 0,
            },
            {
                "id": "mark_resolved",
                "label": "Segna come risolto",
                "verb": "resolve",
                "risk_level": 0,
            },
        ]

        # Create ORM model
        inbox_item = AgentInbox(
            id=inbox_item_id,
            user_id=user_id,
            event_type="document_conflict_detected",
            event_source={
                "source_document_id": str(correlation.source_document_id),
                "target_document_id": str(correlation.target_document_id),
                "correlation_id": str(correlation.id),
                "source_passage": correlation.source_passage,
                "target_passage": correlation.target_passage,
                "source_page": correlation.source_page,
                "target_page": correlation.target_page,
            },
            source_ref_id=correlation.id,
            agent_analysis=conflict_description,
            urgency="today",  # Property 15: conflicts are urgent
            suggested_actions=suggested_actions,
            status="pending",
        )

        self._session.add(inbox_item)
        await self._session.commit()
        await self._session.refresh(inbox_item)

        logger.info(
            "conflict_inbox_item_created",
            inbox_item_id=str(inbox_item_id),
            correlation_id=str(correlation.id),
            source_document_id=str(correlation.source_document_id),
            target_document_id=str(correlation.target_document_id),
        )

        # Convert to domain model
        return AgentInboxItem(
            id=inbox_item.id,
            user_id=inbox_item.user_id,
            event_type=inbox_item.event_type,
            event_source=inbox_item.event_source,
            source_ref_id=inbox_item.source_ref_id,
            agent_analysis=inbox_item.agent_analysis,
            urgency=inbox_item.urgency,
            suggested_actions=inbox_item.suggested_actions,
            status=inbox_item.status,
            chosen_action_id=inbox_item.chosen_action_id,
            chosen_at=inbox_item.chosen_at,
            created_at=inbox_item.created_at,
            expires_at=inbox_item.expires_at,
        )

    def _build_conflict_description(
        self,
        correlation: DocumentCorrelationDomain,
    ) -> str:
        """Build a human-readable conflict description.

        Args:
            correlation: The conflict correlation.

        Returns:
            Conflict description in Italian.
        """
        description = (
            "Ho rilevato dati contraddittori tra due documenti. "
            "È necessaria la tua revisione per risolvere l'incongruenza."
        )

        if correlation.source_passage and correlation.target_passage:
            description += (
                f"\n\nDocumento 1 (pagina {correlation.source_page or '?'}): "
                f'"{correlation.source_passage[:200]}..."'
                f"\n\nDocumento 2 (pagina {correlation.target_page or '?'}): "
                f'"{correlation.target_passage[:200]}..."'
            )

        return description

    def _to_domain(
        self,
        orm_correlation: DocumentCorrelationORM,
    ) -> DocumentCorrelationDomain:
        """Convert ORM model to domain model.

        Args:
            orm_correlation: SQLAlchemy ORM model.

        Returns:
            DocumentCorrelation domain model.
        """
        return DocumentCorrelationDomain(
            id=orm_correlation.id,
            source_document_id=orm_correlation.source_document_id,
            target_document_id=orm_correlation.target_document_id,
            correlation_type=orm_correlation.correlation_type,  # type: ignore[arg-type]
            confidence_score=orm_correlation.confidence_score,
            source_passage=orm_correlation.source_passage,
            target_passage=orm_correlation.target_passage,
            source_page=orm_correlation.source_page,
            target_page=orm_correlation.target_page,
        )
