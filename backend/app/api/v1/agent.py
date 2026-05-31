"""Agent Chat API — query endpoint with message persistence."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db

router = APIRouter(prefix="/agent", tags=["agent"])


class QueryRequest(BaseModel):
    message: str
    session_id: str


class QueryResponse(BaseModel):
    response: str
    session_id: str
    workflow_id: str | None = None
    blocked: bool = False


@router.post("/query", response_model=QueryResponse)
async def agent_query(
    body: QueryRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Process a chat message through the agent, persisting to session."""
    from app.agent.graphs.chat_agent import ChatAgentGraph
    from app.agent.guardrails.guardrail_layer import GuardrailLayer
    from app.api.deps import get_llm
    from app.db.models import ChatMessage, ChatSession

    uid = uuid.UUID(user["sub"])
    sid = uuid.UUID(body.session_id)

    # Verify session ownership
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.user_id == uid)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Persist user message
    user_msg = ChatMessage(session_id=sid, role="user", content=body.message)
    db.add(user_msg)

    # Run agent
    llm = get_llm()
    graph = ChatAgentGraph(llm=llm, guardrails=GuardrailLayer())
    agent_result = await graph.handle_message(body.message, user["sub"], str(sid))

    # Persist agent response
    agent_msg = ChatMessage(
        session_id=sid,
        role="agent",
        content=agent_result["response"],
        blocked=agent_result.get("blocked", False),
    )
    db.add(agent_msg)

    # Update session timestamp (and auto-title on first message)
    from sqlalchemy import func
    session.updated_at = func.now()
    if session.title == "Nuova chat":
        session.title = body.message[:80]

    await db.commit()

    return QueryResponse(
        response=agent_result["response"],
        session_id=str(sid),
        workflow_id=agent_result.get("workflow_id"),
        blocked=agent_result.get("blocked", False),
    )
