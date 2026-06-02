"""Unit tests for ConfirmationFlowService."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.services.confirmation_flow_service import ConfirmationFlowService
from app.db.models import AgentTask, PendingConfirmation


def _wire_mock_session(session: AsyncMock) -> None:
    """Simulate flush linking AgentTask.id to PendingConfirmation.task_id."""

    async def flush_side_effect() -> None:
        tasks = [c[0][0] for c in session.add.call_args_list if isinstance(c[0][0], AgentTask)]
        confs = [c[0][0] for c in session.add.call_args_list if isinstance(c[0][0], PendingConfirmation)]
        for task in tasks:
            if not task.id:
                task.id = uuid.uuid4()
        for conf in confs:
            if tasks and not conf.task_id:
                conf.task_id = tasks[-1].id

    async def refresh_side_effect(obj: object) -> None:
        if isinstance(obj, AgentTask) and not obj.id:
            obj.id = uuid.uuid4()
        if isinstance(obj, PendingConfirmation):
            if not obj.task_id:
                obj.task_id = uuid.uuid4()
            obj.created_at = datetime.now(UTC)

    session.flush = flush_side_effect
    session.refresh = refresh_side_effect


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    _wire_mock_session(session)
    return session


@pytest.fixture
def confirmation_service(mock_session: AsyncMock) -> ConfirmationFlowService:
    return ConfirmationFlowService(mock_session)


class TestConfirmationFlowService:
    def test_risk_level_classification(self, confirmation_service: ConfirmationFlowService) -> None:
        assert confirmation_service.classify_risk_level("delete_document") == 4
        assert confirmation_service.classify_risk_level("send_email") == 3
        assert confirmation_service.classify_risk_level("unknown_action") == 2

    def test_visual_style_for_risk(self, confirmation_service: ConfirmationFlowService) -> None:
        assert confirmation_service.visual_style_for_risk(3) == "yellow_border"
        assert confirmation_service.visual_style_for_risk(4) == "red_border_double_confirm"

    @pytest.mark.asyncio
    async def test_create_confirmation_with_source_attribution(
        self, confirmation_service: ConfirmationFlowService, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        result = await confirmation_service.create_confirmation(
            user_id=user_id,
            action_type="send_email",
            description="Conferma invio email",
            preview={"subject": "Promemoria", "body": "Scadenza imminente"},
            source_attribution={
                "deadline_id": str(uuid.uuid4()),
                "deadline_title": "IVA Q1",
            },
        )

        assert result.risk_level == "3"
        assert result.data_for_review["action_type"] == "send_email"
        assert "source_attribution" in result.data_for_review
        assert result.data_for_review["visual_style"] == "yellow_border"
        assert mock_session.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_batch_grouping(
        self, confirmation_service: ConfirmationFlowService, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        items = [
            {
                "action_type": "export_drive",
                "description": "Export 1",
                "preview": {"filename": "report1.pdf"},
                "source_attribution": {"report_id": "r1"},
            },
            {
                "action_type": "export_email",
                "description": "Export 2",
                "preview": {"recipient": "a@b.com"},
                "source_attribution": {"report_id": "r2"},
            },
        ]

        results = await confirmation_service.create_batch(user_id, items, group_type="report_export")
        assert len(results) == 2
        assert results[0].group_id is not None
        assert results[0].group_id == results[1].group_id
        assert results[0].group_type == "report_export"

    @pytest.mark.asyncio
    async def test_risk_level_distinction(
        self, confirmation_service: ConfirmationFlowService,
    ) -> None:
        low_risk = await confirmation_service.create_confirmation(
            user_id=uuid.uuid4(),
            action_type="custom_action",
            description="Low risk",
            preview={},
            source_attribution={},
            risk_level=2,
        )
        high_risk = await confirmation_service.create_confirmation(
            user_id=uuid.uuid4(),
            action_type="delete_document",
            description="High risk",
            preview={},
            source_attribution={},
        )

        assert low_risk.risk_level == "2"
        assert low_risk.data_for_review["visual_style"] == "standard"
        assert high_risk.risk_level == "4"
        assert high_risk.data_for_review["visual_style"] == "red_border_double_confirm"
