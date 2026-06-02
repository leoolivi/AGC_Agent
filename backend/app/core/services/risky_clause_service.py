"""RiskyClauseService — Storage and retrieval of risky clauses with confidence filtering.

This service manages risky clauses detected in contract documents, providing:
- Clause storage and retrieval by document
- Confidence-based filtering (threshold 0.75 for "uncertain" classification)
- Severity ordering (alto > medio > basso)
- Plain-language explanation validation (max 200 chars)

Requirements: 5, 6
Properties: 11, 12, 13
"""

from __future__ import annotations

import uuid
from typing import Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.clause import RiskyClause as RiskyClauseDomain
from app.db.models import RiskyClause as RiskyClauseORM

logger = structlog.get_logger()

# Confidence threshold for "uncertain" classification (Property 12)
CONFIDENCE_THRESHOLD_UNCERTAIN = 0.75

# Severity ordering for sorting (Property 13)
SEVERITY_ORDER = {"alto": 0, "medio": 1, "basso": 2}


class RiskyClauseService:
    """Service for managing risky clauses detected in contracts."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def store_clause(
        self,
        document_id: uuid.UUID,
        category: Literal[
            "rinnovo_automatico",
            "penale",
            "limitazione_responsabilita",
            "recesso",
            "esclusiva",
            "non_concorrenza",
        ],
        severity: Literal["alto", "medio", "basso"],
        clause_text: str,
        plain_language_explanation: str,
        confidence_score: float,
        page_number: int | None = None,
        paragraph_ref: str | None = None,
    ) -> RiskyClauseDomain:
        """Store a newly detected risky clause.

        This method validates the plain-language explanation length (max 200 chars)
        and confidence score range (0.0-1.0) via Pydantic domain model validation.

        Args:
            document_id: The document containing this clause.
            category: The risk category of the clause.
            severity: The severity level (alto, medio, basso).
            clause_text: The exact text of the clause from the document.
            plain_language_explanation: User-friendly explanation (max 200 chars).
            confidence_score: Confidence score (0.0-1.0).
            page_number: Optional page number where clause appears.
            paragraph_ref: Optional paragraph reference.

        Returns:
            The created RiskyClause domain model.

        Raises:
            ValueError: If plain_language_explanation exceeds 200 chars or
                       confidence_score is out of range (validated by Pydantic).
        """
        clause_id = uuid.uuid4()

        # Create domain model first to trigger Pydantic validation (Property 11)
        domain_clause = RiskyClauseDomain(
            id=clause_id,
            document_id=document_id,
            category=category,
            severity=severity,
            clause_text=clause_text,
            page_number=page_number,
            paragraph_ref=paragraph_ref,
            plain_language_explanation=plain_language_explanation,
            confidence_score=confidence_score,
        )

        # Create ORM model
        orm_clause = RiskyClauseORM(
            id=clause_id,
            document_id=document_id,
            category=category,
            severity=severity,
            clause_text=clause_text,
            page_number=page_number,
            paragraph_ref=paragraph_ref,
            plain_language_explanation=plain_language_explanation,
            confidence_score=confidence_score,
        )

        self._session.add(orm_clause)
        await self._session.commit()
        await self._session.refresh(orm_clause)

        logger.info(
            "risky_clause_stored",
            clause_id=str(clause_id),
            document_id=str(document_id),
            category=category,
            severity=severity,
            confidence_score=confidence_score,
        )

        return domain_clause

    async def store_clauses_batch(
        self,
        document_id: uuid.UUID,
        clauses: list[RiskyClauseDomain],
    ) -> list[RiskyClauseDomain]:
        """Store multiple risky clauses in a single transaction.

        Useful when the RiskyClauseGraph detects multiple clauses in one analysis.

        Args:
            document_id: The document containing these clauses.
            clauses: List of RiskyClause domain models to store.

        Returns:
            List of stored RiskyClause domain models.

        Raises:
            ValueError: If any clause fails Pydantic validation.
        """
        orm_clauses = []
        for clause in clauses:
            # Validate that clause belongs to the specified document
            if clause.document_id != document_id:
                msg = f"Clause {clause.id} document_id mismatch"
                raise ValueError(msg)

            orm_clause = RiskyClauseORM(
                id=clause.id,
                document_id=clause.document_id,
                category=clause.category,
                severity=clause.severity,
                clause_text=clause.clause_text,
                page_number=clause.page_number,
                paragraph_ref=clause.paragraph_ref,
                plain_language_explanation=clause.plain_language_explanation,
                confidence_score=clause.confidence_score,
            )
            orm_clauses.append(orm_clause)

        self._session.add_all(orm_clauses)
        await self._session.commit()

        logger.info(
            "risky_clauses_batch_stored",
            document_id=str(document_id),
            count=len(clauses),
        )

        return clauses

    async def get_clauses_by_document(
        self,
        document_id: uuid.UUID,
        min_confidence: float | None = None,
        category: str | None = None,
    ) -> list[RiskyClauseDomain]:
        """Retrieve all risky clauses for a document with optional filtering.

        Clauses are returned grouped by category and sorted by severity within
        each category (alto > medio > basso) as per Property 13.

        Args:
            document_id: The document ID.
            min_confidence: Optional minimum confidence threshold for filtering.
            category: Optional category filter.

        Returns:
            List of RiskyClause domain models, sorted by severity.
        """
        query = select(RiskyClauseORM).where(RiskyClauseORM.document_id == document_id)

        if min_confidence is not None:
            query = query.where(RiskyClauseORM.confidence_score >= min_confidence)

        if category:
            query = query.where(RiskyClauseORM.category == category)

        # Order by category first, then severity (Property 13)
        query = query.order_by(RiskyClauseORM.category, RiskyClauseORM.severity)

        result = await self._session.execute(query)
        orm_clauses = result.scalars().all()

        # Convert to domain models and apply severity ordering within categories
        domain_clauses = [self._to_domain(c) for c in orm_clauses]

        # Sort by severity within each category using SEVERITY_ORDER
        domain_clauses.sort(key=lambda c: (c.category, SEVERITY_ORDER[c.severity]))

        logger.debug(
            "clauses_retrieved",
            document_id=str(document_id),
            count=len(domain_clauses),
            min_confidence=min_confidence,
            category=category,
        )

        return domain_clauses

    async def get_clause_by_id(self, clause_id: uuid.UUID) -> RiskyClauseDomain | None:
        """Retrieve a single risky clause by ID.

        Args:
            clause_id: The clause ID.

        Returns:
            RiskyClause domain model if found, None otherwise.
        """
        result = await self._session.execute(
            select(RiskyClauseORM).where(RiskyClauseORM.id == clause_id)
        )
        orm_clause = result.scalar_one_or_none()
        return self._to_domain(orm_clause) if orm_clause else None

    async def get_clauses_by_category(
        self,
        document_id: uuid.UUID,
        category: Literal[
            "rinnovo_automatico",
            "penale",
            "limitazione_responsabilita",
            "recesso",
            "esclusiva",
            "non_concorrenza",
        ],
    ) -> list[RiskyClauseDomain]:
        """Retrieve all clauses of a specific category for a document.

        Args:
            document_id: The document ID.
            category: The risk category to filter by.

        Returns:
            List of RiskyClause domain models, sorted by severity.
        """
        return await self.get_clauses_by_document(
            document_id=document_id,
            category=category,
        )

    async def get_high_confidence_clauses(
        self,
        document_id: uuid.UUID,
    ) -> list[RiskyClauseDomain]:
        """Retrieve clauses with confidence >= 0.75 (not uncertain).

        This method implements Property 12: clauses with confidence < 0.75
        are considered "uncertain" and can be filtered out.

        Args:
            document_id: The document ID.

        Returns:
            List of high-confidence RiskyClause domain models.
        """
        return await self.get_clauses_by_document(
            document_id=document_id,
            min_confidence=CONFIDENCE_THRESHOLD_UNCERTAIN,
        )

    async def get_uncertain_clauses(
        self,
        document_id: uuid.UUID,
    ) -> list[RiskyClauseDomain]:
        """Retrieve clauses with confidence < 0.75 (uncertain).

        These clauses should be displayed with a visual indicator
        "Interpretazione incerta" as per Requirement 5.4.

        Args:
            document_id: The document ID.

        Returns:
            List of uncertain RiskyClause domain models.
        """
        query = (
            select(RiskyClauseORM)
            .where(RiskyClauseORM.document_id == document_id)
            .where(RiskyClauseORM.confidence_score < CONFIDENCE_THRESHOLD_UNCERTAIN)
            .order_by(RiskyClauseORM.category, RiskyClauseORM.severity)
        )

        result = await self._session.execute(query)
        orm_clauses = result.scalars().all()

        domain_clauses = [self._to_domain(c) for c in orm_clauses]
        domain_clauses.sort(key=lambda c: (c.category, SEVERITY_ORDER[c.severity]))

        return domain_clauses

    async def delete_clauses_by_document(self, document_id: uuid.UUID) -> int:
        """Delete all risky clauses for a document.

        This is typically called when a document is deleted or re-analyzed.

        Args:
            document_id: The document ID.

        Returns:
            Number of clauses deleted.
        """
        result = await self._session.execute(
            select(RiskyClauseORM).where(RiskyClauseORM.document_id == document_id)
        )
        orm_clauses = result.scalars().all()
        count = len(orm_clauses)

        for clause in orm_clauses:
            await self._session.delete(clause)

        await self._session.commit()

        logger.info(
            "clauses_deleted",
            document_id=str(document_id),
            count=count,
        )

        return count

    async def count_clauses_by_document(self, document_id: uuid.UUID) -> int:
        """Count total risky clauses for a document.

        Args:
            document_id: The document ID.

        Returns:
            Total number of clauses.
        """
        result = await self._session.execute(
            select(RiskyClauseORM).where(RiskyClauseORM.document_id == document_id)
        )
        return len(result.scalars().all())

    async def count_by_severity(
        self,
        document_id: uuid.UUID,
    ) -> dict[str, int]:
        """Count clauses by severity level for a document.

        Args:
            document_id: The document ID.

        Returns:
            Dictionary mapping severity level to count.
        """
        result = await self._session.execute(
            select(RiskyClauseORM).where(RiskyClauseORM.document_id == document_id)
        )
        clauses = result.scalars().all()

        counts = {"alto": 0, "medio": 0, "basso": 0}
        for clause in clauses:
            counts[clause.severity] += 1

        return counts

    def is_uncertain(self, clause: RiskyClauseDomain) -> bool:
        """Check if a clause is uncertain (confidence < 0.75).

        This helper method implements Property 12 for UI components.

        Args:
            clause: The RiskyClause domain model.

        Returns:
            True if confidence < 0.75, False otherwise.
        """
        return clause.confidence_score < CONFIDENCE_THRESHOLD_UNCERTAIN

    def _to_domain(self, orm_clause: RiskyClauseORM) -> RiskyClauseDomain:
        """Convert ORM model to domain model.

        Args:
            orm_clause: SQLAlchemy ORM model.

        Returns:
            RiskyClause domain model.
        """
        return RiskyClauseDomain(
            id=orm_clause.id,
            document_id=orm_clause.document_id,
            category=orm_clause.category,  # type: ignore[arg-type]
            severity=orm_clause.severity,  # type: ignore[arg-type]
            clause_text=orm_clause.clause_text,
            page_number=orm_clause.page_number,
            paragraph_ref=orm_clause.paragraph_ref,
            plain_language_explanation=orm_clause.plain_language_explanation,
            confidence_score=orm_clause.confidence_score,
        )
