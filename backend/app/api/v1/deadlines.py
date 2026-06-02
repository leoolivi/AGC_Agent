"""Deadlines API — CRUD + upcoming."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_owner
from app.db.models import Deadline

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


class CreateDeadlineRequest(BaseModel):
    title: str
    due_date: date
    description: str | None = None
    deadline_type: str = "custom"
    recurrence: str = "none"
    document_id: str | None = None


class UpdateDeadlineRequest(BaseModel):
    title: str | None = None
    due_date: date | None = None
    description: str | None = None
    status: str | None = None


@router.get("")
async def list_deadlines(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Deadline)
        .where(Deadline.user_id == uuid.UUID(user["sub"]))
        .order_by(Deadline.due_date)
    )
    return [
        {
            "id": str(d.id), "title": d.title, "due_date": d.due_date.isoformat(),
            "deadline_type": d.deadline_type, "recurrence": d.recurrence,
            "status": d.status, "source": d.source,
        }
        for d in result.scalars().all()
    ]


@router.get("/upcoming")
async def upcoming_deadlines(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    from datetime import timedelta
    today = date.today()
    cutoff = today + timedelta(days=days)
    result = await db.execute(
        select(Deadline)
        .where(Deadline.user_id == uuid.UUID(user["sub"]))
        .where(Deadline.status == "active")
        .where(Deadline.due_date >= today)
        .where(Deadline.due_date <= cutoff)
        .order_by(Deadline.due_date)
    )
    return [
        {"id": str(d.id), "title": d.title, "due_date": d.due_date.isoformat(), "status": d.status}
        for d in result.scalars().all()
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_deadline(
    body: CreateDeadlineRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    dl = Deadline(
        user_id=uuid.UUID(user["sub"]),
        title=body.title,
        due_date=body.due_date,
        description=body.description,
        deadline_type=body.deadline_type,
        recurrence=body.recurrence,
        document_id=uuid.UUID(body.document_id) if body.document_id else None,
        source="manual",
    )
    db.add(dl)
    await db.commit()
    await db.refresh(dl)
    return {"id": str(dl.id), "title": dl.title, "due_date": dl.due_date.isoformat()}


@router.put("/{deadline_id}")
async def update_deadline(
    deadline_id: str,
    body: UpdateDeadlineRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    dl = await db.get(Deadline, uuid.UUID(deadline_id))
    if dl is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    require_owner(str(dl.user_id), user)
    if body.title is not None:
        dl.title = body.title
    if body.due_date is not None:
        dl.due_date = body.due_date
    if body.description is not None:
        dl.description = body.description
    if body.status is not None:
        dl.status = body.status
    await db.commit()
    return {"id": str(dl.id), "status": "updated"}


@router.post("/{deadline_id}/calendar-event")
async def create_calendar_event(
    deadline_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Propose calendar event creation with HITL (risk level 3)."""
    from app.api.oauth_scopes import validate_source_oauth_scope
    from app.core.services.confirmation_flow_service import ConfirmationFlowService

    await validate_source_oauth_scope(user["sub"], "calendar")

    dl = await db.get(Deadline, uuid.UUID(deadline_id))
    if dl is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    require_owner(str(dl.user_id), user)

    conf_service = ConfirmationFlowService(db)
    confirmation = await conf_service.create_confirmation(
        user_id=uuid.UUID(user["sub"]),
        action_type="create_calendar_event",
        description=f"Crea evento calendario per: {dl.title}",
        preview={
            "title": dl.title,
            "due_date": dl.due_date.isoformat(),
            "description": dl.description or "",
        },
        source_attribution={"deadline_id": str(dl.id), "deadline_title": dl.title},
    )
    return {"status": "pending_confirmation", "confirmation_id": str(confirmation.id)}


@router.post("/{deadline_id}/calendar-event/update-proposal")
async def propose_calendar_update(
    deadline_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Propose calendar event update/cancellation when deadline status changes."""
    from app.core.services.confirmation_flow_service import ConfirmationFlowService

    dl = await db.get(Deadline, uuid.UUID(deadline_id))
    if dl is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    require_owner(str(dl.user_id), user)

    if not dl.calendar_event_id:
        raise HTTPException(status_code=400, detail="No linked calendar event")

    action = "delete_calendar_event" if dl.status in ("completed", "cancelled", "deleted") else "update_calendar_event"
    conf_service = ConfirmationFlowService(db)
    confirmation = await conf_service.create_confirmation(
        user_id=uuid.UUID(user["sub"]),
        action_type=action,
        description=f"Aggiorna evento calendario per: {dl.title}",
        preview={"calendar_event_id": dl.calendar_event_id, "new_status": dl.status},
        source_attribution={"deadline_id": str(dl.id), "calendar_event_id": dl.calendar_event_id},
    )
    return {"status": "pending_confirmation", "confirmation_id": str(confirmation.id)}


@router.delete("/{deadline_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_deadline(
    deadline_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    dl = await db.get(Deadline, uuid.UUID(deadline_id))
    if dl is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    require_owner(str(dl.user_id), user)
    dl.status = "deleted"
    await db.commit()
    return {"id": str(dl.id), "status": "deleted"}
