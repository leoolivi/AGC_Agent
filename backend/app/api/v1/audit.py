"""Audit Log API — read-only endpoint for audit entries."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("")
async def list_audit_log(
    action_type: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get audit log entries with pagination and optional action_type filter."""
    query = select(AuditLog).where(AuditLog.user_id == uuid.UUID(user["sub"]))
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "action_type": e.action_type,
            "tool_name": e.tool_name,
            "input_summary": e.input_summary,
            "output_summary": e.output_summary,
            "risk_score": e.risk_score,
            "status": e.status,
            "llm_model": e.llm_model,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
