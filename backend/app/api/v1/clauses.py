"""Clauses API — risky clauses for documents."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.services.risky_clause_service import RiskyClauseService

router = APIRouter(prefix="/clauses", tags=["clauses"])


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "estratto"
    if score >= 0.60:
        return "inferito"
    return "suggerito"


@router.get("/{document_id}")
async def get_clauses(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = RiskyClauseService(db)
    clauses = await service.get_clauses_by_document(uuid.UUID(document_id))
    return [
        {
            "id": str(c.id),
            "category": c.category,
            "severity": c.severity,
            "clause_text": c.clause_text,
            "page_number": c.page_number,
            "paragraph_ref": c.paragraph_ref,
            "plain_language_explanation": c.plain_language_explanation,
            "confidence_score": c.confidence_score,
            "confidence_label": _confidence_label(c.confidence_score),
            "uncertain": c.confidence_score < 0.75,
        }
        for c in clauses
    ]
