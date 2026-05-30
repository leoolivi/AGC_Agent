"""Confirmations API — HITL approve/reject endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_owner
from app.db.models import AgentTask, PendingConfirmation

router = APIRouter(prefix="/confirmations", tags=["confirmations"])


class ApproveRequest(BaseModel):
    user_comment: str | None = None


class RejectRequest(BaseModel):
    user_comment: str | None = None


# State machine transitions:
# agent_tasks: pending → in_progress → done|failed|skipped (risk ≤ 2)
#              pending → waiting_confirmation → approved → done|rejected (risk ≥ 3)
VALID_TASK_TRANSITIONS = {
    "pending": {"in_progress", "waiting_confirmation"},
    "in_progress": {"done", "failed", "skipped"},
    "waiting_confirmation": {"approved", "rejected"},
    "approved": {"done", "failed"},
}


@router.get("")
async def list_confirmations(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    result = await db.execute(
        select(PendingConfirmation)
        .where(PendingConfirmation.user_id == uuid.UUID(user["sub"]))
        .where(PendingConfirmation.status == "pending")
        .order_by(PendingConfirmation.created_at.desc())
    )
    confirmations = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "task_id": str(c.task_id),
            "description": c.description,
            "data_for_review": c.data_for_review,
            "risk_level": c.risk_level,
            "status": c.status,
            "group_id": str(c.group_id) if c.group_id else None,
            "group_type": c.group_type,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in confirmations
    ]


@router.post("/{confirmation_id}/approve")
async def approve_confirmation(
    confirmation_id: str,
    body: ApproveRequest = ApproveRequest(),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    conf = await db.get(PendingConfirmation, uuid.UUID(confirmation_id))
    if conf is None:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    require_owner(str(conf.user_id), user)

    if conf.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot approve confirmation with status '{conf.status}'",
        )

    conf.status = "approved"
    conf.user_comment = body.user_comment
    conf.resolved_at = datetime.now(timezone.utc)

    # Update associated task
    task = await db.get(AgentTask, conf.task_id)
    if task and task.status == "waiting_confirmation":
        task.status = "approved"

    await db.commit()
    return {"id": str(conf.id), "status": "approved"}


@router.post("/{confirmation_id}/reject")
async def reject_confirmation(
    confirmation_id: str,
    body: RejectRequest = RejectRequest(),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    conf = await db.get(PendingConfirmation, uuid.UUID(confirmation_id))
    if conf is None:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    require_owner(str(conf.user_id), user)

    if conf.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot reject confirmation with status '{conf.status}'",
        )

    conf.status = "rejected"
    conf.user_comment = body.user_comment
    conf.resolved_at = datetime.now(timezone.utc)

    # Update associated task
    task = await db.get(AgentTask, conf.task_id)
    if task:
        task.status = "rejected"

    await db.commit()
    return {"id": str(conf.id), "status": "rejected"}
