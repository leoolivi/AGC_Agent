"""Escalation lifecycle hooks — activation and resolution."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graphs.escalation_draft_graph import EscalationDraftGraph
from app.api.deps import get_escalation_scheduler, get_llm, get_notifier
from app.core.services.escalation_service import EscalationService
from app.core.services.notification_service import NotificationService
from app.db.models import Deadline, EscalationRule as EscalationRuleORM
from sqlalchemy import select

logger = structlog.get_logger()


def _escalation_service(session: AsyncSession) -> EscalationService:
    return EscalationService(
        session, get_escalation_scheduler(), NotificationService(get_notifier())
    )


async def activate_escalation_for_deadline(session: AsyncSession, deadline_id: uuid.UUID) -> None:
    """Activate escalation when deadline times out without user action."""
    deadline = await session.get(Deadline, deadline_id)
    if not deadline or deadline.status != "active":
        return

    rule_id = deadline.escalation_rule_id
    if not rule_id:
        result = await session.execute(
            select(EscalationRuleORM)
            .where(EscalationRuleORM.user_id == deadline.user_id)
            .where(EscalationRuleORM.deadline_type == deadline.deadline_type)
            .where(EscalationRuleORM.is_active.is_(True))
            .limit(1)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return
        rule_id = rule.id

    service = _escalation_service(session)
    await service.activate_for_deadline(deadline_id, rule_id)
    logger.info("escalation_activated", deadline_id=str(deadline_id))


async def resolve_escalation_on_user_action(session: AsyncSession, deadline_id: uuid.UUID) -> None:
    """Resolve active escalation when user acts on related inbox item."""
    service = _escalation_service(session)
    await service.resolve_for_deadline(deadline_id)


async def generate_escalation_draft(
    deadline: dict,
    channel: str,
    message_template: str,
    recipient: str = "",
) -> dict:
    """Generate draft via EscalationDraftGraph."""
    graph = EscalationDraftGraph(get_llm())
    return await graph.run(deadline, channel, message_template, recipient)  # type: ignore[arg-type]
