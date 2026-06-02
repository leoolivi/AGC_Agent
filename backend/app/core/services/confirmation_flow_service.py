"""ConfirmationFlowService — unified HITL confirmation creation and batch grouping.

Provides consistent PendingConfirmation creation with source attribution,
batch grouping of related confirmations, and risk-level classification.

Requirements: 18
Properties: 23, 30
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.pending_confirmation import PendingConfirmation as PendingConfirmationDomain
from app.db.models import AgentTask, PendingConfirmation

logger = structlog.get_logger()

ACTION_RISK_LEVELS: dict[str, int] = {
    "send_email": 3,
    "export_drive": 3,
    "export_email": 3,
    "create_calendar_event": 3,
    "update_calendar_event": 3,
    "delete_calendar_event": 3,
    "escalation_email": 3,
    "escalation_calendar": 3,
    "delete_document": 4,
    "bulk_action": 3,
}

VISUAL_STYLES: dict[int, str] = {
    2: "standard",
    3: "yellow_border",
    4: "red_border_double_confirm",
}


class ConfirmationFlowService:
    """Unified service for HITL confirmation creation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def classify_risk_level(self, action_type: str) -> int:
        """Classify risk level for an action type."""
        return ACTION_RISK_LEVELS.get(action_type, 2)

    def visual_style_for_risk(self, risk_level: int) -> str:
        """Return visual style identifier for UI rendering."""
        return VISUAL_STYLES.get(risk_level, "standard")

    async def create_confirmation(
        self,
        user_id: uuid.UUID,
        action_type: str,
        description: str,
        preview: dict[str, Any],
        source_attribution: dict[str, Any],
        risk_level: int | None = None,
        tool_args: dict[str, Any] | None = None,
        group_id: uuid.UUID | None = None,
        group_type: str | None = None,
    ) -> PendingConfirmationDomain:
        """Create a PendingConfirmation with consistent structure."""
        effective_risk = risk_level if risk_level is not None else self.classify_risk_level(action_type)
        visual_style = self.visual_style_for_risk(effective_risk)

        task = AgentTask(
            user_id=user_id,
            action_type=action_type,
            tool_name=action_type,
            tool_args=tool_args or {},
            risk_score=effective_risk,
            status="waiting_confirmation",
        )
        self._session.add(task)
        await self._session.flush()

        data_for_review = {
            "action_type": action_type,
            "preview": preview,
            "source_attribution": source_attribution,
            "visual_style": visual_style,
        }

        conf_id = uuid.uuid4()
        orm_conf = PendingConfirmation(
            id=conf_id,
            task_id=task.id,
            user_id=user_id,
            description=description,
            data_for_review=data_for_review,
            risk_level=str(effective_risk),
            status="pending",
            group_id=group_id,
            group_type=group_type,
        )
        self._session.add(orm_conf)
        await self._session.commit()
        await self._session.refresh(orm_conf)

        logger.info(
            "confirmation_created",
            confirmation_id=str(conf_id),
            action_type=action_type,
            risk_level=effective_risk,
            group_id=str(group_id) if group_id else None,
        )
        return self._to_domain(orm_conf)

    async def create_batch(
        self,
        user_id: uuid.UUID,
        items: list[dict[str, Any]],
        group_type: str = "batch",
    ) -> list[PendingConfirmationDomain]:
        """Create a batch of related confirmations sharing a group_id."""
        group_id = uuid.uuid4()
        confirmations: list[PendingConfirmationDomain] = []

        for item in items:
            conf = await self.create_confirmation(
                user_id=user_id,
                action_type=item["action_type"],
                description=item["description"],
                preview=item.get("preview", {}),
                source_attribution=item.get("source_attribution", {}),
                risk_level=item.get("risk_level"),
                tool_args=item.get("tool_args"),
                group_id=group_id,
                group_type=group_type,
            )
            confirmations.append(conf)

        logger.info(
            "confirmation_batch_created",
            group_id=str(group_id),
            count=len(confirmations),
            group_type=group_type,
        )
        return confirmations

    async def get_pending_by_group(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[PendingConfirmationDomain]:
        result = await self._session.execute(
            select(PendingConfirmation)
            .where(PendingConfirmation.group_id == group_id)
            .where(PendingConfirmation.user_id == user_id)
            .where(PendingConfirmation.status == "pending")
        )
        return [self._to_domain(c) for c in result.scalars().all()]

    async def get_pending_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[PendingConfirmationDomain]:
        result = await self._session.execute(
            select(PendingConfirmation)
            .where(PendingConfirmation.user_id == user_id)
            .where(PendingConfirmation.status == "pending")
            .order_by(PendingConfirmation.created_at.desc())
        )
        return [self._to_domain(c) for c in result.scalars().all()]

    def _to_domain(self, orm: PendingConfirmation) -> PendingConfirmationDomain:
        return PendingConfirmationDomain(
            id=orm.id,
            task_id=orm.task_id,
            user_id=orm.user_id,
            description=orm.description,
            data_for_review=orm.data_for_review,
            risk_level=orm.risk_level,
            status=orm.status,
            user_comment=orm.user_comment,
            group_id=orm.group_id,
            group_type=orm.group_type,
            created_at=orm.created_at or datetime.now(UTC),
            resolved_at=orm.resolved_at,
        )
