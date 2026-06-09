"i""Chat sessions API — CRUD for persistent chat conversations."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    blocked: bool
    created_at: str


class CreateSessionRequest(BaseModel):
    title: str = "Nuova chat"


class RenameSessionRequest(BaseModel):
    title: str


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionOut]:
    uid = uuid.UUID(user["sub"])
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == uid)
        .order_by(ChatSession.updated_at.desc())
    )
    return [
        SessionOut(
            id=str(s.id), title=s.title,
            created_at=s.created_at.isoformat(), updated_at=s.updated_at.isoformat(),
        )
        for s in result.scalars().all()
    ]


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = ChatSession(user_id=uuid.UUID(user["sub"]), title=body.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionOut(
        id=str(session.id), title=session.title,
        created_at=session.created_at.isoformat(), updated_at=session.updated_at.isoformat(),
    )


@router.patch("/sessions/{session_id}", response_model=SessionOut)
async def rename_session(
    session_id: str,
    body: RenameSessionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    uid = uuid.UUID(user["sub"])
    sid = uuid.UUID(session_id)
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.user_id == uid)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = body.title
    await db.commit()
    await db.refresh(session)
    return SessionOut(
        id=str(session.id), title=session.title,
        created_at=session.created_at.isoformat(), updated_at=session.updated_at.isoformat(),
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    uid = uuid.UUID(user["sub"])
    sid = uuid.UUID(session_id)
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.user_id == uid)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")
    await db.execute(delete(ChatSession).where(ChatSession.id == sid))
    await db.commit()
    return Response(status_code=204)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def list_messages(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    uid = uuid.UUID(user["sub"])
    sid = uuid.UUID(session_id)
    # Verify ownership
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.user_id == uid)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == sid).order_by(ChatMessage.created_at)
    )
    return [
        MessageOut(
            id=str(m.id), role=m.role, content=m.content,
            blocked=m.blocked, created_at=m.created_at.isoformat(),
        )
        for m in msgs.scalars().all()
    ]
