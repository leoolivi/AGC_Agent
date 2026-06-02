"""Unit tests for EscalationService."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.dummy.escalation_scheduler import DummyEscalationSchedulerAdapter
from app.adapters.dummy.notifier import DummyNotifierAdapter
from app.core.domain.escalation import EscalationStep
from app.core.services.escalation_service import EscalationService
from app.core.services.notification_service import NotificationService


def _make_step(delay: int = 3600, channel: str = "in_app") -> EscalationStep:
    return EscalationStep(
        delay_seconds=delay,
        channel=channel,  # type: ignore[arg-type]
        recipient="user@test.com",
        message_template="Reminder: {deadline_title} due {due_date}",
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def escalation_service(mock_session: AsyncMock) -> EscalationService:
    scheduler = DummyEscalationSchedulerAdapter()
    notifier = DummyNotifierAdapter()
    notification = NotificationService(notifier)
    return EscalationService(mock_session, scheduler, notification)


class TestEscalationService:
    @pytest.mark.asyncio
    async def test_create_rule_validates_steps(
        self, escalation_service: EscalationService, mock_session: AsyncMock
    ) -> None:
        steps = [_make_step(3600), _make_step(7200, "email")]
        rule = await escalation_service.create_rule(
            user_id=uuid.uuid4(),
            name="Test Rule",
            deadline_type="fiscale",
            steps=steps,
        )
        assert len(rule.steps) == 2
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_steps_rejected(self) -> None:
        from app.core.domain.escalation import EscalationRule

        with pytest.raises(ValueError, match="strictly increasing"):
            EscalationRule(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                name="Bad",
                deadline_type="fiscale",
                steps=[
                    _make_step(7200),
                    _make_step(3600),
                ],
            )

    @pytest.mark.asyncio
    async def test_execute_in_app_step(
        self, escalation_service: EscalationService, mock_session: AsyncMock
    ) -> None:
        execution_id = uuid.uuid4()
        deadline_id = uuid.uuid4()
        rule_id = uuid.uuid4()
        user_id = uuid.uuid4()

        orm_exec = MagicMock()
        orm_exec.id = execution_id
        orm_exec.deadline_id = deadline_id
        orm_exec.rule_id = rule_id
        orm_exec.current_step = 0
        orm_exec.status = "active"
        orm_exec.history = []
        orm_exec.next_step_job_id = "job-1"

        orm_rule = MagicMock()
        orm_rule.steps = [_make_step(3600, "in_app").model_dump()]

        deadline = MagicMock()
        deadline.id = deadline_id
        deadline.user_id = user_id
        deadline.title = "IVA Q1"
        deadline.due_date = date(2026, 4, 30)

        mock_session.get = AsyncMock(side_effect=lambda model, id: {
            execution_id: orm_exec,
            rule_id: orm_rule,
            deadline_id: deadline,
        }.get(id))

        result = await escalation_service.execute_current_step(execution_id)
        assert result.current_step == 1
        assert len(result.history) == 1
        assert result.history[0].result == "sent"

    @pytest.mark.asyncio
    async def test_email_step_creates_hitl(
        self, escalation_service: EscalationService, mock_session: AsyncMock
    ) -> None:
        execution_id = uuid.uuid4()
        deadline_id = uuid.uuid4()
        rule_id = uuid.uuid4()
        user_id = uuid.uuid4()

        orm_exec = MagicMock()
        orm_exec.id = execution_id
        orm_exec.deadline_id = deadline_id
        orm_exec.rule_id = rule_id
        orm_exec.current_step = 0
        orm_exec.status = "active"
        orm_exec.history = []
        orm_exec.next_step_job_id = None

        orm_rule = MagicMock()
        orm_rule.steps = [_make_step(3600, "email").model_dump()]

        deadline = MagicMock()
        deadline.id = deadline_id
        deadline.user_id = user_id
        deadline.title = "Contratto XYZ"
        deadline.due_date = date(2026, 6, 1)

        mock_session.get = AsyncMock(side_effect=lambda model, id: {
            execution_id: orm_exec,
            rule_id: orm_rule,
            deadline_id: deadline,
        }.get(id))

        result = await escalation_service.execute_current_step(execution_id)
        assert result.history[0].result == "pending_hitl"
        assert mock_session.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_resolution_cancels_scheduler(
        self, escalation_service: EscalationService, mock_session: AsyncMock
    ) -> None:
        scheduler = escalation_service._scheduler
        assert isinstance(scheduler, DummyEscalationSchedulerAdapter)

        execution_id = uuid.uuid4()
        orm_exec = MagicMock()
        orm_exec.id = execution_id
        orm_exec.status = "active"
        orm_exec.next_step_job_id = "job-resolvable"
        orm_exec.history = []
        orm_exec.deadline_id = uuid.uuid4()
        orm_exec.rule_id = uuid.uuid4()
        orm_exec.current_step = 1

        scheduler.scheduled.append(("exec", 3600, "job-resolvable"))
        mock_session.get = AsyncMock(return_value=orm_exec)

        result = await escalation_service.resolve(execution_id)
        assert result.status == "resolved"
        assert "job-resolvable" in scheduler.cancelled
