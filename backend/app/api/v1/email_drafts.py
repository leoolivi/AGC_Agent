"""Email Drafts API — CRUD + approve + send."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_owner
from app.db.models import EmailDraft

router = APIRouter(prefix="/email-drafts", tags=["email-drafts"])


class UpdateDraftRequest(BaseModel):
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    to_addresses: list[str] | None = None


@router.get("")
async def list_drafts(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(EmailDraft)
        .where(EmailDraft.user_id == uuid.UUID(user["sub"]))
        .order_by(EmailDraft.created_at.desc())
    )
    return [
        {
            "id": str(d.id), "subject": d.subject, "to_addresses": d.to_addresses,
            "status": d.status, "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in result.scalars().all()
    ]


@router.get("/{draft_id}")
async def get_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    draft = await db.get(EmailDraft, uuid.UUID(draft_id))
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    require_owner(str(draft.user_id), user)
    return {
        "id": str(draft.id), "subject": draft.subject, "to_addresses": draft.to_addresses,
        "body_html": draft.body_html, "body_text": draft.body_text,
        "status": draft.status, "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }


@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    body: UpdateDraftRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    draft = await db.get(EmailDraft, uuid.UUID(draft_id))
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    require_owner(str(draft.user_id), user)
    if draft.status != "pending_review":
        raise HTTPException(status_code=422, detail="Can only edit drafts in pending_review")
    if body.subject is not None:
        draft.subject = body.subject
    if body.body_text is not None:
        draft.body_text = body.body_text
        # Auto-convert markdown to HTML
        import re
        html = body.body_text
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = html.replace("\n\n", "</p><p>").replace("\n", "<br>")
        draft.body_html = f"<p>{html}</p>"
    if body.body_html is not None and body.body_text is None:
        draft.body_html = body.body_html
    if body.to_addresses is not None:
        draft.to_addresses = body.to_addresses
    await db.commit()
    return {"id": str(draft.id), "status": "updated"}


@router.post("/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    draft = await db.get(EmailDraft, uuid.UUID(draft_id))
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    require_owner(str(draft.user_id), user)
    if draft.status != "pending_review":
        raise HTTPException(status_code=422, detail="Can only approve pending_review drafts")
    draft.status = "approved"
    draft.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(draft.id), "status": "approved"}


@router.post("/{draft_id}/send")
async def send_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    draft = await db.get(EmailDraft, uuid.UUID(draft_id))
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    require_owner(str(draft.user_id), user)
    if draft.status != "approved":
        raise HTTPException(status_code=422, detail="Can only send approved drafts")
    draft.status = "sent"
    draft.sent_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(draft.id), "status": "sent"}


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    draft = await db.get(EmailDraft, uuid.UUID(draft_id))
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    require_owner(str(draft.user_id), user)
    await db.delete(draft)
    await db.commit()
    return {"status": "deleted"}
