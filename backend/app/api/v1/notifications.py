"""Notifications API — list, mark read."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == uuid.UUID(user["sub"]))
        .order_by(Notification.read, Notification.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(n.id), "title": n.title, "body": n.body,
            "level": n.level, "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in result.scalars().all()
    ]


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    await db.execute(
        update(Notification)
        .where(Notification.id == uuid.UUID(notification_id))
        .where(Notification.user_id == uuid.UUID(user["sub"]))
        .values(read=True)
    )
    await db.commit()
    return {"status": "read"}


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == uuid.UUID(user["sub"]))
        .where(Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return {"status": "all_read"}
