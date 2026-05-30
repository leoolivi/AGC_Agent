"""Agent Inbox API — list, act, dismiss, unread-count, trigger-triage."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_owner
from app.db.models import AgentInbox

router = APIRouter(prefix="/inbox", tags=["inbox"])

# Urgency rank for ordering: immediate=0, today=1, this_week=2, low=3
URGENCY_RANK = {"immediate": 0, "today": 1, "this_week": 2, "low": 3}


class ActRequest(BaseModel):
    action_id: str


@router.get("")
async def list_inbox(
    status_filter: str | None = None,
    urgency: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List inbox items ordered by urgency rank then created_at DESC."""
    query = select(AgentInbox).where(AgentInbox.user_id == uuid.UUID(user["sub"]))
    if status_filter:
        query = query.where(AgentInbox.status == status_filter)
    if urgency:
        query = query.where(AgentInbox.urgency == urgency)

    # Order by urgency rank (using CASE), then created_at DESC
    from sqlalchemy import case

    urgency_order = case(
        (AgentInbox.urgency == "immediate", 0),
        (AgentInbox.urgency == "today", 1),
        (AgentInbox.urgency == "this_week", 2),
        else_=3,
    )
    query = query.order_by(urgency_order, AgentInbox.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "event_type": i.event_type,
            "agent_analysis": i.agent_analysis,
            "urgency": i.urgency,
            "suggested_actions": i.suggested_actions,
            "status": i.status,
            "chosen_action_id": i.chosen_action_id,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "expires_at": i.expires_at.isoformat() if i.expires_at else None,
        }
        for i in items
    ]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, int]:
    result = await db.execute(
        select(func.count(AgentInbox.id))
        .where(AgentInbox.user_id == uuid.UUID(user["sub"]))
        .where(AgentInbox.status == "pending")
    )
    count = result.scalar() or 0
    return {"unread_count": count}


@router.post("/{item_id}/act")
async def act_on_item(
    item_id: str,
    body: ActRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    item = await db.get(AgentInbox, uuid.UUID(item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    require_owner(str(item.user_id), user)

    # Validate action_id
    valid_ids = [a.get("id") for a in (item.suggested_actions or [])]
    if body.action_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action_id: {body.action_id}",
        )

    item.status = "acted"
    item.chosen_action_id = body.action_id
    item.chosen_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(item.id), "status": "acted", "chosen_action_id": body.action_id}


@router.post("/{item_id}/dismiss")
async def dismiss_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    item = await db.get(AgentInbox, uuid.UUID(item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    require_owner(str(item.user_id), user)

    item.status = "dismissed"
    await db.commit()
    return {"id": str(item.id), "status": "dismissed"}


@router.post("/trigger-triage")
async def trigger_triage(
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Manually trigger triage for the user. Returns immediately."""
    # In production, this would enqueue a background task
    return {"status": "triggered", "user_id": user["sub"]}
