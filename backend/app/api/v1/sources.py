"""Sources API — CRUD for monitored sources."""
from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.dummy.source_monitor import DummySourceMonitorAdapter
from app.api.deps import get_current_user, get_db, get_source_monitor
from app.api.oauth_scopes import check_oauth_scopes, validate_source_oauth_scope
from app.core.domain.source import CalendarSourceConfig, DriveSourceConfig, GmailSourceConfig
from app.core.services.source_monitor_service import SourceMonitorService
from app.db.models import MonitoredSource
from sqlalchemy import select

router = APIRouter(prefix="/sources", tags=["sources"])


class CreateSourceRequest(BaseModel):
    source_type: Literal["drive", "gmail", "calendar"]
    config: dict[str, Any]


class UpdateSourceRequest(BaseModel):
    config: dict[str, Any] | None = None
    status: Literal["active", "error", "paused"] | None = None


def _parse_config(source_type: str, config: dict[str, Any]) -> DriveSourceConfig | GmailSourceConfig | CalendarSourceConfig:
    if source_type == "drive":
        return DriveSourceConfig(**config)
    if source_type == "gmail":
        return GmailSourceConfig(**config)
    return CalendarSourceConfig(**config)


@router.get("")
async def list_sources(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = SourceMonitorService(db, get_source_monitor())
    sources = await service.list_sources(uuid.UUID(user["sub"]))
    return [
        {
            "id": str(s.id),
            "source_type": s.source_type,
            "config": s.config.model_dump(),
            "status": s.status,
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
            "last_sync_count": s.last_sync_count,
        }
        for s in sources
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_source(
    body: CreateSourceRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    await validate_source_oauth_scope(user["sub"], body.source_type)
    try:
        config = _parse_config(body.source_type, body.config)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e
    service = SourceMonitorService(db, get_source_monitor())
    try:
        source = await service.create_source(uuid.UUID(user["sub"]), body.source_type, config)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"id": str(source.id), "source_type": source.source_type, "status": source.status}


@router.get("/{source_id}")
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = SourceMonitorService(db, get_source_monitor())
    source = await service.get_source(uuid.UUID(source_id), uuid.UUID(user["sub"]))
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return {
        "id": str(source.id),
        "source_type": source.source_type,
        "config": source.config.model_dump(),
        "status": source.status,
        "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
        "last_sync_count": source.last_sync_count,
    }


@router.put("/{source_id}")
async def update_source(
    source_id: str,
    body: UpdateSourceRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = SourceMonitorService(db, get_source_monitor())
    existing = await service.get_source(uuid.UUID(source_id), uuid.UUID(user["sub"]))
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")

    config = None
    if body.config:
        await validate_source_oauth_scope(user["sub"], existing.source_type)
        config = _parse_config(existing.source_type, body.config)

    updated = await service.update_source(
        uuid.UUID(source_id), uuid.UUID(user["sub"]), config=config, status=body.status
    )
    assert updated
    return {"id": str(updated.id), "status": updated.status}


@router.delete("/{source_id}", status_code=status.HTTP_200_OK)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    service = SourceMonitorService(db, get_source_monitor())
    deleted = await service.delete_source(uuid.UUID(source_id), uuid.UUID(user["sub"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"status": "deleted"}


@router.get("/{source_id}/status")
async def source_status(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(MonitoredSource)
        .where(MonitoredSource.id == uuid.UUID(source_id))
        .where(MonitoredSource.user_id == uuid.UUID(user["sub"]))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    scope_status = await check_oauth_scopes(user["sub"], source.source_type)
    return {
        "id": str(source.id),
        "source_type": source.source_type,
        "status": source.status,
        "error_count": source.error_count,
        "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
        "last_sync_count": source.last_sync_count,
        "oauth": scope_status,
    }


@router.post("/{source_id}/reconnect")
async def reconnect_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = SourceMonitorService(db, DummySourceMonitorAdapter())
    ok = await service.reset_error_count(uuid.UUID(source_id), uuid.UUID(user["sub"]))
    if not ok:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"status": "reconnected"}
