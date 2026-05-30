"""AgentState — LangGraph state definition.

All agent state passes through this TypedDict. No global state allowed.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    user_id: str
    session_id: str
    triggering_event: dict | None
    messages: Annotated[list, add_messages]
    active_workflow_id: str | None
    workflow_args: dict
    planned_steps: list[dict]
    current_step_index: int
    executed_steps: list[dict]
    pending_confirmations: list[dict]
    inbox_item_id: str | None
    final_response: str
    errors: list[str]
