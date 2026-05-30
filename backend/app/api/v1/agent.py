"""Agent Chat API — query endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


class QueryRequest(BaseModel):
    message: str
    session_id: str | None = None


class QueryResponse(BaseModel):
    response: str
    session_id: str
    workflow_id: str | None = None
    blocked: bool = False


@router.post("/query", response_model=QueryResponse)
async def agent_query(
    body: QueryRequest,
    user: dict = Depends(get_current_user),
) -> QueryResponse:
    """Process a chat message through the agent."""
    import json
    from app.api.deps import get_llm
    from app.agent.graphs.chat_agent import ChatAgentGraph
    from app.agent.guardrails.guardrail_layer import GuardrailLayer
    from app.agent.workflows.templates import build_registry

    session_id = body.session_id or str(uuid.uuid4())
    llm = get_llm()

    graph = ChatAgentGraph(llm=llm, registry=build_registry(), guardrails=GuardrailLayer())
    result = await graph.handle_message(body.message, user["sub"], session_id)

    return QueryResponse(
        response=result["response"],
        session_id=session_id,
        workflow_id=result.get("workflow_id"),
        blocked=result.get("blocked", False),
    )
