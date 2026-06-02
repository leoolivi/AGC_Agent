"""EscalationService — escalation rule CRUD and state machine execution.

Manages escalation rules, state machine transitions (Idle→Step1→...→Exhausted/Resolved),
HITL creation for email/calendar steps, and resolution on user action.

Requirements: 9, 10
Properties: 18, 19, 20
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.escalation import (
    EscalationExecution as EscalationExecutionDomain,
)
from app.core.domain.escalation import (
    EscalationHistoryEntry,
    EscalationRule,
    EscalationStep,
)
from app.core.ports.escalation_scheduler import EscalationSchedulerPort
from app.core.services.notification_service import NotificationService
from app.db.models import AgentTask, Deadline, EscalationExecution, EscalationRule as EscalationRuleORM
from app.db.models import PendingConfirmation

logger = structlog.get_logger()


class EscalationService:
    """Service for escalation rules and execution state machine."""

    def __init__(
        self,
        session: AsyncSession,
        scheduler: EscalationSchedulerPort,
        notification_service: NotificationService,
    ) -> None:
        self._session = session
        self._scheduler = scheduler
        self._notification = notification_service

    async def create_rule(
        self,
        user_id: uuid.UUID,
        name: str,
        deadline_type: Literal["fiscale", "contrattuale", "pagamento", "generico"],
        steps: list[EscalationStep],
        is_active: bool = True,
    ) -> EscalationRule:
        """Create a new escalation rule with validated steps."""
        rule_id = uuid.uuid4()
        domain_rule = EscalationRule(
            id=rule_id,
            user_id=user_id,
            name=name,
            deadline_type=deadline_type,
            steps=steps,
            is_active=is_active,
        )

        orm_rule = EscalationRuleORM(
            id=rule_id,
            user_id=user_id,
            name=name,
            deadline_type=deadline_type,
            steps=[s.model_dump() for s in steps],
            is_active=is_active,
        )
        self._session.add(orm_rule)
        await self._session.commit()
        await self._session.refresh(orm_rule)

        logger.info("escalation_rule_created", rule_id=str(rule_id), user_id=str(user_id))
        return domain_rule

    async def get_rule(
        self,
        rule_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> EscalationRule | None:
        result = await self._session.execute(
            select(EscalationRuleORM)
            .where(EscalationRuleORM.id == rule_id)
            .where(EscalationRuleORM.user_id == user_id)
        )
        orm = result.scalar_one_or_none()
        return self._rule_to_domain(orm) if orm else None

    async def list_rules(
        self,
        user_id: uuid.UUID,
        deadline_type: str | None = None,
        active_only: bool = False,
    ) -> list[EscalationRule]:
        query = select(EscalationRuleORM).where(EscalationRuleORM.user_id == user_id)
        if deadline_type:
            query = query.where(EscalationRuleORM.deadline_type == deadline_type)
        if active_only:
            query = query.where(EscalationRuleORM.is_active.is_(True))
        query = query.order_by(EscalationRuleORM.created_at.desc())

        result = await self._session.execute(query)
        return [self._rule_to_domain(r) for r in result.scalars().all()]

    async def update_rule(
        self,
        rule_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        steps: list[EscalationStep] | None = None,
        is_active: bool | None = None,
    ) -> EscalationRule | None:
        result = await self._session.execute(
            select(EscalationRuleORM)
            .where(EscalationRuleORM.id == rule_id)
            .where(EscalationRuleORM.user_id == user_id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return None

        if name is not None:
            orm.name = name
        if steps is not None:
            EscalationRule(
                id=rule_id,
                user_id=user_id,
                name=orm.name,
                deadline_type=orm.deadline_type,  # type: ignore[arg-type]
                steps=steps,
            )
            orm.steps = [s.model_dump() for s in steps]
        if is_active is not None:
            orm.is_active = is_active

        orm.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(orm)
        return self._rule_to_domain(orm)

    async def delete_rule(self, rule_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(EscalationRuleORM)
            .where(EscalationRuleORM.id == rule_id)
            .where(EscalationRuleORM.user_id == user_id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return False
        await self._session.delete(orm)
        await self._session.commit()
        return True

    async def activate_for_deadline(
        self,
        deadline_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> EscalationExecutionDomain:
        """Start escalation for a deadline. Schedules the first step."""
        deadline = await self._session.get(Deadline, deadline_id)
        if deadline is None:
            msg = f"Deadline {deadline_id} not found"
            raise ValueError(msg)

        rule = await self._session.get(EscalationRuleORM, rule_id)
        if rule is None or not rule.is_active:
            msg = f"Escalation rule {rule_id} not found or inactive"
            raise ValueError(msg)

        existing = await self._session.execute(
            select(EscalationExecution)
            .where(EscalationExecution.deadline_id == deadline_id)
            .where(EscalationExecution.status == "active")
        )
        if existing.scalar_one_or_none():
            msg = f"Active escalation already exists for deadline {deadline_id}"
            raise ValueError(msg)

        execution_id = uuid.uuid4()
        steps = [EscalationStep(**s) for s in rule.steps]
        job_id = await self._scheduler.schedule_step(
            str(execution_id),
            steps[0].delay_seconds,
        )

        orm_exec = EscalationExecution(
            id=execution_id,
            deadline_id=deadline_id,
            rule_id=rule_id,
            current_step=0,
            status="active",
            next_step_job_id=job_id,
            history=[],
        )
        self._session.add(orm_exec)
        await self._session.commit()
        await self._session.refresh(orm_exec)

        logger.info(
            "escalation_activated",
            execution_id=str(execution_id),
            deadline_id=str(deadline_id),
            rule_id=str(rule_id),
        )
        return self._execution_to_domain(orm_exec)

    async def execute_current_step(self, execution_id: uuid.UUID) -> EscalationExecutionDomain:
        """Execute the current escalation step and schedule the next one if any."""
        orm_exec = await self._session.get(EscalationExecution, execution_id)
        if orm_exec is None:
            msg = f"Escalation execution {execution_id} not found"
            raise ValueError(msg)
        if orm_exec.status != "active":
            msg = f"Escalation {execution_id} is not active (status={orm_exec.status})"
            raise ValueError(msg)

        rule = await self._session.get(EscalationRuleORM, orm_exec.rule_id)
        if rule is None:
            msg = f"Rule {orm_exec.rule_id} not found"
            raise ValueError(msg)

        deadline = await self._session.get(Deadline, orm_exec.deadline_id)
        if deadline is None:
            msg = f"Deadline {orm_exec.deadline_id} not found"
            raise ValueError(msg)

        steps = [EscalationStep(**s) for s in rule.steps]
        step_index = orm_exec.current_step
        if step_index >= len(steps):
            orm_exec.status = "exhausted"
            await self._cancel_scheduled_job(orm_exec)
            await self._session.commit()
            return self._execution_to_domain(orm_exec)

        step = steps[step_index]
        result = await self._execute_step(
            step=step,
            step_index=step_index,
            deadline=deadline,
            user_id=deadline.user_id,
        )

        history = list(orm_exec.history)
        history.append(
            {
                "step": step_index,
                "timestamp": datetime.now(UTC).isoformat(),
                "channel": step.channel,
                "result": result,
            }
        )
        orm_exec.history = history
        orm_exec.current_step = step_index + 1

        if orm_exec.current_step >= len(steps):
            orm_exec.status = "exhausted"
            await self._cancel_scheduled_job(orm_exec)
        else:
            prev_delay = steps[step_index].delay_seconds
            next_delay = steps[orm_exec.current_step].delay_seconds
            delay_until_next = next_delay - prev_delay
            job_id = await self._scheduler.schedule_step(str(execution_id), delay_until_next)
            orm_exec.next_step_job_id = job_id

        await self._session.commit()
        await self._session.refresh(orm_exec)

        logger.info(
            "escalation_step_executed",
            execution_id=str(execution_id),
            step=step_index,
            channel=step.channel,
            result=result,
        )
        return self._execution_to_domain(orm_exec)

    async def resolve(
        self,
        execution_id: uuid.UUID,
        resolved_by: str = "user_action",
    ) -> EscalationExecutionDomain:
        """Resolve an active escalation (user acted on deadline/inbox)."""
        orm_exec = await self._session.get(EscalationExecution, execution_id)
        if orm_exec is None:
            msg = f"Escalation execution {execution_id} not found"
            raise ValueError(msg)

        await self._cancel_scheduled_job(orm_exec)
        orm_exec.status = "resolved"
        orm_exec.resolved_at = datetime.now(UTC)
        orm_exec.resolved_by = resolved_by
        await self._session.commit()
        await self._session.refresh(orm_exec)

        logger.info("escalation_resolved", execution_id=str(execution_id), resolved_by=resolved_by)
        return self._execution_to_domain(orm_exec)

    async def resolve_for_deadline(self, deadline_id: uuid.UUID) -> EscalationExecutionDomain | None:
        """Resolve any active escalation for a deadline."""
        result = await self._session.execute(
            select(EscalationExecution)
            .where(EscalationExecution.deadline_id == deadline_id)
            .where(EscalationExecution.status == "active")
        )
        orm_exec = result.scalar_one_or_none()
        if not orm_exec:
            return None
        return await self.resolve(orm_exec.id)

    async def cancel(self, execution_id: uuid.UUID) -> EscalationExecutionDomain:
        """Manually cancel an active escalation."""
        orm_exec = await self._session.get(EscalationExecution, execution_id)
        if orm_exec is None:
            msg = f"Escalation execution {execution_id} not found"
            raise ValueError(msg)

        await self._cancel_scheduled_job(orm_exec)
        orm_exec.status = "cancelled"
        orm_exec.resolved_at = datetime.now(UTC)
        orm_exec.resolved_by = "manual_cancel"
        await self._session.commit()
        await self._session.refresh(orm_exec)
        return self._execution_to_domain(orm_exec)

    async def get_execution(self, execution_id: uuid.UUID) -> EscalationExecutionDomain | None:
        orm_exec = await self._session.get(EscalationExecution, execution_id)
        return self._execution_to_domain(orm_exec) if orm_exec else None

    async def get_status_for_deadline(
        self,
        deadline_id: uuid.UUID,
    ) -> EscalationExecutionDomain | None:
        result = await self._session.execute(
            select(EscalationExecution)
            .where(EscalationExecution.deadline_id == deadline_id)
            .order_by(EscalationExecution.started_at.desc())
        )
        orm_exec = result.scalars().first()
        return self._execution_to_domain(orm_exec) if orm_exec else None

    async def _execute_step(
        self,
        step: EscalationStep,
        step_index: int,
        deadline: Deadline,
        user_id: uuid.UUID,
    ) -> Literal["sent", "pending_hitl", "failed", "skipped"]:
        message = step.message_template.format(
            deadline_title=deadline.title,
            due_date=str(deadline.due_date),
        )

        if step.channel == "in_app":
            ok = await self._notification.dispatch(
                user_id=str(user_id),
                title=f"Promemoria scadenza: {deadline.title}",
                body=message,
                level="warning",
                channels=["inapp"],
            )
            return "sent" if ok else "failed"

        action_type = "escalation_email" if step.channel == "email" else "escalation_calendar"
        risk_score = 3
        task = AgentTask(
            user_id=user_id,
            action_type=action_type,
            tool_name=action_type,
            tool_args={
                "deadline_id": str(deadline.id),
                "recipient": step.recipient,
                "message": message,
                "step_index": step_index,
            },
            risk_score=risk_score,
            status="waiting_confirmation",
        )
        self._session.add(task)
        await self._session.flush()

        confirmation = PendingConfirmation(
            task_id=task.id,
            user_id=user_id,
            description=f"Conferma {step.channel} escalation: {deadline.title}",
            data_for_review={
                "action_type": action_type,
                "preview": message,
                "source_attribution": {
                    "deadline_id": str(deadline.id),
                    "deadline_title": deadline.title,
                    "due_date": str(deadline.due_date),
                },
                "recipient": step.recipient,
                "channel": step.channel,
                "visual_style": "yellow_border",
            },
            risk_level=str(risk_score),
            status="pending",
        )
        self._session.add(confirmation)
        await self._session.flush()
        return "pending_hitl"

    async def _cancel_scheduled_job(self, orm_exec: EscalationExecution) -> None:
        if orm_exec.next_step_job_id:
            try:
                await self._scheduler.cancel_step(orm_exec.next_step_job_id)
            except ValueError:
                pass
            orm_exec.next_step_job_id = None

    def _rule_to_domain(self, orm: EscalationRuleORM) -> EscalationRule:
        steps = [EscalationStep(**s) for s in orm.steps]
        return EscalationRule(
            id=orm.id,
            user_id=orm.user_id,
            name=orm.name,
            deadline_type=orm.deadline_type,  # type: ignore[arg-type]
            steps=steps,
            is_active=orm.is_active,
        )

    def _execution_to_domain(self, orm: EscalationExecution) -> EscalationExecutionDomain:
        history = [
            EscalationHistoryEntry(
                step=h["step"],
                timestamp=datetime.fromisoformat(h["timestamp"])
                if isinstance(h["timestamp"], str)
                else h["timestamp"],
                channel=h["channel"],
                result=h["result"],  # type: ignore[arg-type]
            )
            for h in orm.history
        ]
        return EscalationExecutionDomain(
            id=orm.id,
            deadline_id=orm.deadline_id,
            rule_id=orm.rule_id,
            current_step=orm.current_step,
            status=orm.status,  # type: ignore[arg-type]
            history=history,
        )
