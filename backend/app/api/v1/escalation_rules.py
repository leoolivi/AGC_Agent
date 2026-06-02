"""Escalation rules API."""
from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_escalation_scheduler, get_notifier
from app.core.domain.escalation import EscalationStep
from app.core.services.escalation_service import EscalationService
from app.core.services.notification_service import NotificationService

router = APIRouter(prefix="/escalation-rules", tags=["escalation"])


class StepRequest(BaseModel):
    delay_seconds: int
    channel: Literal["in_app", "email", "calendar"]
    recipient: str
    message_template: str


class CreateRuleRequest(BaseModel):
    name: str
    deadline_type: Literal["fiscale", "contrattuale", "pagamento", "generico"]
    steps: list[StepRequest]
    is_active: bool = True


class UpdateRuleRequest(BaseModel):
    name: str | None = None
    steps: list[StepRequest] | None = None
    is_active: bool | None = None


def _get_service(db: AsyncSession) -> EscalationService:
    return EscalationService(db, get_escalation_scheduler(), NotificationService(get_notifier()))


@router.get("")
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = _get_service(db)
    rules = await service.list_rules(uuid.UUID(user["sub"]))
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "deadline_type": r.deadline_type,
            "steps": [s.model_dump() for s in r.steps],
            "is_active": r.is_active,
        }
        for r in rules
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: CreateRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    steps = [EscalationStep(**s.model_dump()) for s in body.steps]
    service = _get_service(db)
    try:
        rule = await service.create_rule(
            uuid.UUID(user["sub"]), body.name, body.deadline_type, steps, body.is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"id": str(rule.id), "name": rule.name}


@router.get("/{rule_id}")
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = _get_service(db)
    rule = await service.get_rule(uuid.UUID(rule_id), uuid.UUID(user["sub"]))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {
        "id": str(rule.id),
        "name": rule.name,
        "deadline_type": rule.deadline_type,
        "steps": [s.model_dump() for s in rule.steps],
        "is_active": rule.is_active,
    }


@router.put("/{rule_id}")
async def update_rule(
    rule_id: str,
    body: UpdateRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    steps = [EscalationStep(**s.model_dump()) for s in body.steps] if body.steps else None
    service = _get_service(db)
    try:
        rule = await service.update_rule(
            uuid.UUID(rule_id), uuid.UUID(user["sub"]),
            name=body.name, steps=steps, is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"id": str(rule.id), "name": rule.name}


@router.delete("/{rule_id}", status_code=status.HTTP_200_OK)
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    service = _get_service(db)
    if not await service.delete_rule(uuid.UUID(rule_id), uuid.UUID(user["sub"])):
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}


status_router = APIRouter(prefix="/escalation-status", tags=["escalation"])


@status_router.get("/{deadline_id}")
async def escalation_status(
    deadline_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = _get_service(db)
    execution = await service.get_status_for_deadline(uuid.UUID(deadline_id))
    if not execution:
        return {"deadline_id": deadline_id, "status": "idle", "history": []}
    return {
        "deadline_id": deadline_id,
        "execution_id": str(execution.id),
        "status": execution.status,
        "current_step": execution.current_step,
        "history": [h.model_dump(mode="json") for h in execution.history],
    }
