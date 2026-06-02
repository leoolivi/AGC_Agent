"""DossierService — Dossier creation, retrieval, and completeness tracking.

This service manages logical groupings of correlated documents (dossiers) with:
- Dossier creation and retrieval
- Document grouping based on correlations
- Completeness tracking with missing item classification
- Auto-update on new correlations

Requirements: 8
Properties: 17
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.correlation import (
    Dossier as DossierDomain,
)
from app.core.domain.correlation import (
    DossierDocument as DossierDocumentDomain,
)
from app.core.domain.correlation import (
    MissingItem,
)
from app.db.models import DocumentCorrelation as DocumentCorrelationORM
from app.db.models import Dossier as DossierORM
from app.db.models import DossierDocument as DossierDocumentORM

logger = structlog.get_logger()


class DossierService:
    """Service for managing dossiers (logical document groupings)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def create_dossier(
        self,
        user_id: uuid.UUID,
        title: str,
        dossier_type: str | None = None,
        document_ids: list[uuid.UUID] | None = None,
    ) -> DossierDomain:
        """Create a new dossier with optional initial documents.

        Args:
            user_id: The user who owns this dossier.
            title: The dossier title.
            dossier_type: Optional dossier type (e.g., "contratto_quadro",
                         "fascicolo_fornitore").
            document_ids: Optional list of document IDs to add to the dossier.

        Returns:
            The created Dossier domain model.
        """
        dossier_id = uuid.uuid4()

        # Create ORM model
        orm_dossier = DossierORM(
            id=dossier_id,
            user_id=user_id,
            title=title,
            dossier_type=dossier_type,
            completeness_status="incomplete",
            missing_items=[],
        )

        self._session.add(orm_dossier)

        # Add documents if provided
        if document_ids:
            for doc_id in document_ids:
                dossier_doc = DossierDocumentORM(
                    dossier_id=dossier_id,
                    document_id=doc_id,
                    role=None,
                )
                self._session.add(dossier_doc)

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "dossier_created",
            dossier_id=str(dossier_id),
            user_id=str(user_id),
            title=title,
            dossier_type=dossier_type,
            document_count=len(document_ids) if document_ids else 0,
        )

        # Fetch documents to build complete domain model
        documents = await self._get_dossier_documents(dossier_id)

        return self._to_domain(orm_dossier, documents)

    async def get_dossier_by_id(
        self,
        dossier_id: uuid.UUID,
    ) -> DossierDomain | None:
        """Retrieve a dossier by ID with all its documents.

        Args:
            dossier_id: The dossier ID.

        Returns:
            Dossier domain model if found, None otherwise.
        """
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            return None

        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def get_dossiers_by_user(
        self,
        user_id: uuid.UUID,
        dossier_type: str | None = None,
        completeness_status: Literal["complete", "incomplete"] | None = None,
    ) -> list[DossierDomain]:
        """Retrieve all dossiers for a user with optional filtering.

        Args:
            user_id: The user ID.
            dossier_type: Optional filter by dossier type.
            completeness_status: Optional filter by completeness status.

        Returns:
            List of Dossier domain models.
        """
        query = select(DossierORM).where(DossierORM.user_id == user_id)

        if dossier_type:
            query = query.where(DossierORM.dossier_type == dossier_type)

        if completeness_status:
            query = query.where(DossierORM.completeness_status == completeness_status)

        # Order by most recently updated first
        query = query.order_by(DossierORM.updated_at.desc())

        result = await self._session.execute(query)
        orm_dossiers = result.scalars().all()

        # Fetch documents for each dossier
        dossiers = []
        for orm_dossier in orm_dossiers:
            documents = await self._get_dossier_documents(orm_dossier.id)
            dossiers.append(self._to_domain(orm_dossier, documents))

        logger.debug(
            "dossiers_retrieved",
            user_id=str(user_id),
            count=len(dossiers),
            dossier_type=dossier_type,
            completeness_status=completeness_status,
        )

        return dossiers

    async def get_incomplete_dossiers(
        self,
        user_id: uuid.UUID,
    ) -> list[DossierDomain]:
        """Retrieve all incomplete dossiers for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of incomplete Dossier domain models.
        """
        return await self.get_dossiers_by_user(
            user_id=user_id,
            completeness_status="incomplete",
        )

    async def add_document_to_dossier(
        self,
        dossier_id: uuid.UUID,
        document_id: uuid.UUID,
        role: str | None = None,
    ) -> DossierDomain:
        """Add a document to an existing dossier.

        Args:
            dossier_id: The dossier ID.
            document_id: The document ID to add.
            role: Optional role for this document in the dossier
                 (e.g., "contratto_principale", "fattura", "allegato").

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found or document already in dossier.
        """
        # Check if dossier exists
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        # Check if document already in dossier
        existing = await self._session.execute(
            select(DossierDocumentORM).where(
                DossierDocumentORM.dossier_id == dossier_id,
                DossierDocumentORM.document_id == document_id,
            )
        )
        if existing.scalar_one_or_none():
            msg = f"Document {document_id} already in dossier {dossier_id}"
            raise ValueError(msg)

        # Add document
        dossier_doc = DossierDocumentORM(
            dossier_id=dossier_id,
            document_id=document_id,
            role=role,
        )
        self._session.add(dossier_doc)

        # Update dossier timestamp
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "document_added_to_dossier",
            dossier_id=str(dossier_id),
            document_id=str(document_id),
            role=role,
        )

        # Fetch updated documents
        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def remove_document_from_dossier(
        self,
        dossier_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DossierDomain:
        """Remove a document from a dossier.

        Args:
            dossier_id: The dossier ID.
            document_id: The document ID to remove.

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found or document not in dossier.
        """
        # Check if dossier exists
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        # Find and remove document
        result = await self._session.execute(
            select(DossierDocumentORM).where(
                DossierDocumentORM.dossier_id == dossier_id,
                DossierDocumentORM.document_id == document_id,
            )
        )
        dossier_doc = result.scalar_one_or_none()

        if not dossier_doc:
            msg = f"Document {document_id} not in dossier {dossier_id}"
            raise ValueError(msg)

        await self._session.delete(dossier_doc)

        # Update dossier timestamp
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "document_removed_from_dossier",
            dossier_id=str(dossier_id),
            document_id=str(document_id),
        )

        # Fetch updated documents
        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def update_dossier_role(
        self,
        dossier_id: uuid.UUID,
        document_id: uuid.UUID,
        role: str | None,
    ) -> DossierDomain:
        """Update the role of a document in a dossier.

        Args:
            dossier_id: The dossier ID.
            document_id: The document ID.
            role: New role for the document (None to clear role).

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found or document not in dossier.
        """
        # Check if dossier exists
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        # Find document
        result = await self._session.execute(
            select(DossierDocumentORM).where(
                DossierDocumentORM.dossier_id == dossier_id,
                DossierDocumentORM.document_id == document_id,
            )
        )
        dossier_doc = result.scalar_one_or_none()

        if not dossier_doc:
            msg = f"Document {document_id} not in dossier {dossier_id}"
            raise ValueError(msg)

        # Update role
        dossier_doc.role = role

        # Update dossier timestamp
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "dossier_role_updated",
            dossier_id=str(dossier_id),
            document_id=str(document_id),
            role=role,
        )

        # Fetch updated documents
        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def update_completeness(
        self,
        dossier_id: uuid.UUID,
        completeness_status: Literal["complete", "incomplete"],
        missing_items: list[MissingItem] | None = None,
    ) -> DossierDomain:
        """Update the completeness status and missing items of a dossier.

        This method is typically called after analyzing correlations to determine
        if a dossier is complete or has missing documents.

        Args:
            dossier_id: The dossier ID.
            completeness_status: New completeness status.
            missing_items: Optional list of missing items. If None, existing
                          missing items are preserved.

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found.
        """
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        # Update completeness status
        orm_dossier.completeness_status = completeness_status

        # Update missing items if provided
        if missing_items is not None:
            orm_dossier.missing_items = [
                {"description": item.description, "certainty": item.certainty}
                for item in missing_items
            ]

        # Update timestamp
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "dossier_completeness_updated",
            dossier_id=str(dossier_id),
            completeness_status=completeness_status,
            missing_items_count=len(missing_items) if missing_items else 0,
        )

        # Fetch documents
        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def add_missing_item(
        self,
        dossier_id: uuid.UUID,
        description: str,
        certainty: Literal["certain", "probable"],
    ) -> DossierDomain:
        """Add a missing item to a dossier's missing items list.

        Args:
            dossier_id: The dossier ID.
            description: Description of the missing item.
            certainty: Certainty level ("certain" for explicit references,
                      "probable" for inferred missing items).

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found.
        """
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        # Add missing item
        missing_items = list(orm_dossier.missing_items)
        missing_items.append({"description": description, "certainty": certainty})
        orm_dossier.missing_items = missing_items

        # Set status to incomplete
        orm_dossier.completeness_status = "incomplete"

        # Update timestamp
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "missing_item_added",
            dossier_id=str(dossier_id),
            description=description,
            certainty=certainty,
        )

        # Fetch documents
        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def remove_missing_item(
        self,
        dossier_id: uuid.UUID,
        description: str,
    ) -> DossierDomain:
        """Remove a missing item from a dossier's missing items list.

        This is typically called when a previously missing document is found
        and added to the dossier.

        Args:
            dossier_id: The dossier ID.
            description: Description of the missing item to remove.

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found.
        """
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        # Remove missing item
        missing_items = [
            item for item in orm_dossier.missing_items if item["description"] != description
        ]
        orm_dossier.missing_items = missing_items

        # Update completeness status if no missing items remain
        if not missing_items:
            orm_dossier.completeness_status = "complete"

        # Update timestamp
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "missing_item_removed",
            dossier_id=str(dossier_id),
            description=description,
            new_status=orm_dossier.completeness_status,
        )

        # Fetch documents
        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def auto_group_correlated_documents(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DossierDomain | None:
        """Automatically create or update a dossier based on document correlations.

        This method implements Property 17: documents connected by correlations
        (directly or transitively) are grouped into the same dossier.

        Args:
            user_id: The user who owns the documents.
            document_id: The document ID to group with its correlations.

        Returns:
            The created or updated Dossier domain model, or None if no
            correlations found.
        """
        # Find all correlations for this document
        result = await self._session.execute(
            select(DocumentCorrelationORM).where(
                (DocumentCorrelationORM.source_document_id == document_id)
                | (DocumentCorrelationORM.target_document_id == document_id)
            )
        )
        correlations = result.scalars().all()

        if not correlations:
            logger.debug(
                "no_correlations_for_auto_grouping",
                document_id=str(document_id),
            )
            return None

        # Collect all related document IDs (transitive closure)
        related_doc_ids = {document_id}
        for correlation in correlations:
            related_doc_ids.add(correlation.source_document_id)
            related_doc_ids.add(correlation.target_document_id)

        # Check if any of these documents are already in a dossier
        result = await self._session.execute(
            select(DossierDocumentORM).where(DossierDocumentORM.document_id.in_(related_doc_ids))
        )
        existing_dossier_docs = result.scalars().all()

        if existing_dossier_docs:
            # Use existing dossier and add missing documents
            dossier_id = existing_dossier_docs[0].dossier_id

            # Get existing document IDs in this dossier
            existing_doc_ids = {dd.document_id for dd in existing_dossier_docs}

            # Add documents not yet in dossier
            for doc_id in related_doc_ids - existing_doc_ids:
                dossier_doc = DossierDocumentORM(
                    dossier_id=dossier_id,
                    document_id=doc_id,
                    role=None,
                )
                self._session.add(dossier_doc)

            # Update dossier timestamp
            result = await self._session.execute(
                select(DossierORM).where(DossierORM.id == dossier_id)
            )
            orm_dossier = result.scalar_one()
            orm_dossier.updated_at = datetime.now()

            await self._session.commit()

            logger.info(
                "dossier_auto_updated",
                dossier_id=str(dossier_id),
                document_id=str(document_id),
                added_documents=len(related_doc_ids - existing_doc_ids),
            )

            return await self.get_dossier_by_id(dossier_id)

        else:
            # Create new dossier
            title = f"Fascicolo automatico - {len(related_doc_ids)} documenti"
            dossier = await self.create_dossier(
                user_id=user_id,
                title=title,
                dossier_type="auto_generated",
                document_ids=list(related_doc_ids),
            )

            logger.info(
                "dossier_auto_created",
                dossier_id=str(dossier.id),
                document_id=str(document_id),
                document_count=len(related_doc_ids),
            )

            return dossier

    async def update_dossier_title(
        self,
        dossier_id: uuid.UUID,
        title: str,
    ) -> DossierDomain:
        """Update a dossier's title.

        Args:
            dossier_id: The dossier ID.
            title: New title.

        Returns:
            Updated Dossier domain model.

        Raises:
            ValueError: If dossier not found.
        """
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        orm_dossier.title = title
        orm_dossier.updated_at = datetime.now()

        await self._session.commit()
        await self._session.refresh(orm_dossier)

        logger.info(
            "dossier_title_updated",
            dossier_id=str(dossier_id),
            title=title,
        )

        documents = await self._get_dossier_documents(dossier_id)
        return self._to_domain(orm_dossier, documents)

    async def delete_dossier(
        self,
        dossier_id: uuid.UUID,
    ) -> None:
        """Delete a dossier and all its document associations.

        Note: This does not delete the documents themselves, only the dossier
        grouping.

        Args:
            dossier_id: The dossier ID.

        Raises:
            ValueError: If dossier not found.
        """
        result = await self._session.execute(select(DossierORM).where(DossierORM.id == dossier_id))
        orm_dossier = result.scalar_one_or_none()

        if not orm_dossier:
            msg = f"Dossier {dossier_id} not found"
            raise ValueError(msg)

        await self._session.delete(orm_dossier)
        await self._session.commit()

        logger.info(
            "dossier_deleted",
            dossier_id=str(dossier_id),
        )

    async def count_dossiers_by_user(
        self,
        user_id: uuid.UUID,
    ) -> int:
        """Count total dossiers for a user.

        Args:
            user_id: The user ID.

        Returns:
            Total number of dossiers.
        """
        dossiers = await self.get_dossiers_by_user(user_id)
        return len(dossiers)

    async def get_dossier_by_document(
        self,
        document_id: uuid.UUID,
    ) -> list[DossierDomain]:
        """Find all dossiers containing a specific document.

        A document can belong to multiple dossiers.

        Args:
            document_id: The document ID.

        Returns:
            List of Dossier domain models containing this document.
        """
        result = await self._session.execute(
            select(DossierDocumentORM).where(DossierDocumentORM.document_id == document_id)
        )
        dossier_docs = result.scalars().all()

        dossiers = []
        for dossier_doc in dossier_docs:
            dossier = await self.get_dossier_by_id(dossier_doc.dossier_id)
            if dossier:
                dossiers.append(dossier)

        return dossiers

    async def _get_dossier_documents(
        self,
        dossier_id: uuid.UUID,
    ) -> list[DossierDocumentDomain]:
        """Fetch all documents for a dossier.

        Args:
            dossier_id: The dossier ID.

        Returns:
            List of DossierDocument domain models.
        """
        result = await self._session.execute(
            select(DossierDocumentORM).where(DossierDocumentORM.dossier_id == dossier_id)
        )
        orm_docs = result.scalars().all()

        return [
            DossierDocumentDomain(
                document_id=doc.document_id,
                role=doc.role,
            )
            for doc in orm_docs
        ]

    def _to_domain(
        self,
        orm_dossier: DossierORM,
        documents: list[DossierDocumentDomain],
    ) -> DossierDomain:
        """Convert ORM model to domain model.

        Args:
            orm_dossier: SQLAlchemy ORM model.
            documents: List of DossierDocument domain models.

        Returns:
            Dossier domain model.
        """
        # Convert missing_items from JSONB to MissingItem objects
        missing_items = [
            MissingItem(
                description=item["description"],
                certainty=item["certainty"],  # type: ignore[typeddict-item]
            )
            for item in orm_dossier.missing_items
        ]

        return DossierDomain(
            id=orm_dossier.id,
            user_id=orm_dossier.user_id,
            title=orm_dossier.title,
            dossier_type=orm_dossier.dossier_type,
            completeness_status=orm_dossier.completeness_status,  # type: ignore[arg-type]
            missing_items=missing_items,
            documents=documents,
        )
