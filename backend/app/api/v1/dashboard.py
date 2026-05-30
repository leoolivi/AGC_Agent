"""Dashboard API — overview counters."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import AgentInbox, Deadline, EmailDraft, PendingConfirmation

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    uid = uuid.UUID(user["sub"])
    today = date.today()

    # Deadline semaphore
    red = await db.scalar(
        select(func.count(Deadline.id))
        .where(Deadline.user_id == uid, Deadline.status == "active", Deadline.due_date < today)
    ) or 0
    yellow = await db.scalar(
        select(func.count(Deadline.id))
        .where(Deadline.user_id == uid, Deadline.status == "active",
               Deadline.due_date >= today, Deadline.due_date <= today + timedelta(days=7))
    ) or 0
    green = await db.scalar(
        select(func.count(Deadline.id))
        .where(Deadline.user_id == uid, Deadline.status == "active",
               Deadline.due_date > today + timedelta(days=7),
               Deadline.due_date <= today + timedelta(days=30))
    ) or 0

    # Pending confirmations
    pending_confirmations = await db.scalar(
        select(func.count(PendingConfirmation.id))
        .where(PendingConfirmation.user_id == uid, PendingConfirmation.status == "pending")
    ) or 0

    # Pending drafts
    pending_drafts = await db.scalar(
        select(func.count(EmailDraft.id))
        .where(EmailDraft.user_id == uid, EmailDraft.status == "pending_review")
    ) or 0

    # Inbox pending
    inbox_pending = await db.scalar(
        select(func.count(AgentInbox.id))
        .where(AgentInbox.user_id == uid, AgentInbox.status == "pending")
    ) or 0

    return {
        "deadlines": {"red": red, "yellow": yellow, "green": green},
        "pending_confirmations": pending_confirmations,
        "pending_drafts": pending_drafts,
        "inbox_pending": inbox_pending,
    }
