"""Settings API — user preferences."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    notification_settings: dict | None = None


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    u = await db.get(User, uuid.UUID(user["sub"]))
    if not u:
        return {"notification_settings": {}}
    return {
        "email": u.email,
        "name": u.name,
        "notification_settings": u.notification_settings or {},
    }


@router.put("")
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    u = await db.get(User, uuid.UUID(user["sub"]))
    if u and body.notification_settings is not None:
        u.notification_settings = body.notification_settings
        await db.commit()
    return {"status": "updated"}
