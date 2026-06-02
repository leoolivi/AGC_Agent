"""Correlations API — cross-document correlations."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.services.cross_document_service import CrossDocumentService

router = APIRouter(prefix="/correlations", tags=["correlations"])


@router.get("/{document_id}")
async def get_correlations(
    document_id: str,
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = CrossDocumentService(db)
    correlations = await service.get_correlations_by_document(
        uuid.UUID(document_id),
        include_hidden=include_hidden,
    )
    return [
        {
            "id": str(c.id),
            "source_document_id": str(c.source_document_id),
            "target_document_id": str(c.target_document_id),
            "correlation_type": c.correlation_type,
            "confidence_score": c.confidence_score,
            "confidence_level": service.classify_confidence(c),
            "source_passage": c.source_passage,
            "target_passage": c.target_passage,
            "source_page": c.source_page,
            "target_page": c.target_page,
        }
        for c in correlations
    ]
