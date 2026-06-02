"""Dossiers API — document grouping and completeness."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.services.dossier_service import DossierService

router = APIRouter(prefix="/dossiers", tags=["dossiers"])


class CreateDossierRequest(BaseModel):
    title: str
    dossier_type: str | None = None
    document_ids: list[str] | None = None


def _serialize_dossier(d: object) -> dict[str, Any]:
    return {
        "id": str(d.id),  # type: ignore[attr-defined]
        "title": d.title,  # type: ignore[attr-defined]
        "dossier_type": d.dossier_type,  # type: ignore[attr-defined]
        "completeness_status": d.completeness_status,  # type: ignore[attr-defined]
        "missing_items": [{"description": m.description, "certainty": m.certainty} for m in d.missing_items],  # type: ignore[attr-defined]
        "documents": [{"document_id": str(doc.document_id), "role": doc.role} for doc in d.documents],  # type: ignore[attr-defined]
    }


@router.get("")
async def list_dossiers(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = DossierService(db)
    dossiers = await service.get_dossiers_by_user(uuid.UUID(user["sub"]))
    return [_serialize_dossier(d) for d in dossiers]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_dossier(
    body: CreateDossierRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = DossierService(db)
    doc_ids = [uuid.UUID(d) for d in body.document_ids] if body.document_ids else None
    dossier = await service.create_dossier(
        user_id=uuid.UUID(user["sub"]),
        title=body.title,
        dossier_type=body.dossier_type,
        document_ids=doc_ids,
    )
    return _serialize_dossier(dossier)


@router.get("/{dossier_id}")
async def get_dossier(
    dossier_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = DossierService(db)
    dossier = await service.get_dossier_by_id(uuid.UUID(dossier_id))
    if not dossier or dossier.user_id != uuid.UUID(user["sub"]):
        raise HTTPException(status_code=404, detail="Dossier not found")
    return _serialize_dossier(dossier)
