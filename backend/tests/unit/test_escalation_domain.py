"""Unit tests for escalation domain models."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.core.domain.escalation import (
    EscalationExecution,
    EscalationHistoryEntry,
    EscalationRule,
    EscalationStep,
)


def _make_step(
    delay_seconds: int = 3600,
    channel: str = "in_app",
    recipient: str = "user123",
    message_template: str = "Reminder: {deadline}",
) -> EscalationStep:
    """Helper to create a valid EscalationStep."""
    return EscalationStep(
        delay_seconds=delay_seconds,
        channel=channel,  # type: ignore[arg-type]
        recipient=recipient,
        message_template=message_template,
    )


def _make_rule(steps: list[EscalationStep] | None = None) -> EscalationRule:
    """Helper to create a valid EscalationRule."""
    if steps is None:
        steps = [_make_step()]
    return EscalationRule(
        id=uuid4(),
        user_id=uuid4(),
        name="Test Rule",
        deadline_type="fiscale",
        steps=steps,
    )


class TestEscalationStep:
    """Tests for EscalationStep validation."""

    def test_valid_step(self) -> None:
        step = _make_step()
        assert step.delay_seconds == 3600
        assert step.channel == "in_app"
        assert step.recipient == "user123"

    def test_delay_below_minimum_raises(self) -> None:
        with pytest.raises(ValueError, match="delay_seconds must be >= 3600"):
            _make_step(delay_seconds=1800)

    def test_delay_above_maximum_raises(self) -> None:
        with pytest.raises(ValueError, match="delay_seconds must be <= 604800"):
            _make_step(delay_seconds=700_000)

    def test_empty_recipient_raises(self) -> None:
        with pytest.raises(ValueError, match="recipient must not be empty"):
            _make_step(recipient="")

    def test_whitespace_only_recipient_raises(self) -> None:
        with pytest.raises(ValueError, match="recipient must not be empty"):
            _make_step(recipient="   ")

    def test_empty_message_template_raises(self) -> None:
        with pytest.raises(ValueError, match="message_template must not be empty"):
            _make_step(message_template="")

    def test_whitespace_only_message_template_raises(self) -> None:
        with pytest.raises(ValueError, match="message_template must not be empty"):
            _make_step(message_template="  \t  ")

    def test_all_channels_valid(self) -> None:
        for channel in ("in_app", "email", "calendar"):
            step = _make_step(channel=channel)
            assert step.channel == channel


class TestEscalationRule:
    """Tests for EscalationRule validation."""

    def test_valid_rule_single_step(self) -> None:
        rule = _make_rule()
        assert len(rule.steps) == 1
        assert rule.is_active is True

    def test_valid_rule_multiple_steps(self) -> None:
        steps = [
            _make_step(delay_seconds=3600),
            _make_step(delay_seconds=7200, channel="email", recipient="a@b.com"),
            _make_step(delay_seconds=14400, channel="calendar", recipient="cal_id"),
        ]
        rule = _make_rule(steps=steps)
        assert len(rule.steps) == 3

    def test_max_five_steps_allowed(self) -> None:
        steps = [_make_step(delay_seconds=3600 * (i + 1)) for i in range(5)]
        rule = _make_rule(steps=steps)
        assert len(rule.steps) == 5

    def test_more_than_five_steps_raises(self) -> None:
        steps = [_make_step(delay_seconds=3600 * (i + 1)) for i in range(6)]
        with pytest.raises(ValueError, match="at most 5 steps"):
            _make_rule(steps=steps)

    def test_empty_steps_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 1 step"):
            _make_rule(steps=[])

    def test_non_increasing_delays_raises(self) -> None:
        steps = [
            _make_step(delay_seconds=7200),
            _make_step(delay_seconds=3600),
        ]
        with pytest.raises(ValueError, match="strictly increasing"):
            _make_rule(steps=steps)

    def test_equal_delays_raises(self) -> None:
        steps = [
            _make_step(delay_seconds=3600),
            _make_step(delay_seconds=3600),
        ]
        with pytest.raises(ValueError, match="strictly increasing"):
            _make_rule(steps=steps)

    def test_all_deadline_types_valid(self) -> None:
        for dtype in ("fiscale", "contrattuale", "pagamento", "generico"):
            rule = EscalationRule(
                id=uuid4(),
                user_id=uuid4(),
                name="Test",
                deadline_type=dtype,  # type: ignore[arg-type]
                steps=[_make_step()],
            )
            assert rule.deadline_type == dtype


class TestEscalationExecution:
    """Tests for EscalationExecution model."""

    def test_defaults(self) -> None:
        execution = EscalationExecution(
            id=uuid4(), deadline_id=uuid4(), rule_id=uuid4()
        )
        assert execution.current_step == 0
        assert execution.status == "active"
        assert execution.history == []

    def test_all_statuses_valid(self) -> None:
        for status in ("active", "resolved", "exhausted", "cancelled"):
            execution = EscalationExecution(
                id=uuid4(),
                deadline_id=uuid4(),
                rule_id=uuid4(),
                status=status,  # type: ignore[arg-type]
            )
            assert execution.status == status


class TestEscalationHistoryEntry:
    """Tests for EscalationHistoryEntry model."""

    def test_valid_entry(self) -> None:
        entry = EscalationHistoryEntry(
            step=0,
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            channel="email",
            result="sent",
        )
        assert entry.step == 0
        assert entry.result == "sent"

    def test_all_results_valid(self) -> None:
        for result in ("sent", "pending_hitl", "failed", "skipped"):
            entry = EscalationHistoryEntry(
                step=1,
                timestamp=datetime.now(),
                channel="in_app",
                result=result,  # type: ignore[arg-type]
            )
            assert entry.result == result
