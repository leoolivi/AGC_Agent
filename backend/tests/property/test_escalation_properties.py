"""Property-based tests for EscalationService domain validation."""
from __future__ import annotations

import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.domain.escalation import EscalationRule, EscalationStep


def _step(delay: int) -> EscalationStep:
    return EscalationStep(
        delay_seconds=delay,
        channel="in_app",
        recipient="user@test.com",
        message_template="Reminder: {deadline_title}",
    )


@given(st.lists(st.integers(min_value=3600, max_value=604800), min_size=1, max_size=5, unique=True))
@settings(max_examples=15)
def test_increasing_delays_valid(sorted_delays: list[int]) -> None:
    delays = sorted(sorted_delays)
    steps = [_step(d) for d in delays]
    rule = EscalationRule(
        id=uuid.uuid4(), user_id=uuid.uuid4(), name="Test",
        deadline_type="fiscale", steps=steps,
    )
    assert len(rule.steps) <= 5
    for i in range(1, len(rule.steps)):
        assert rule.steps[i].delay_seconds > rule.steps[i - 1].delay_seconds


@given(st.lists(st.integers(min_value=3600, max_value=604800), min_size=6, max_size=8))
@settings(max_examples=5)
def test_max_five_steps_rejected(extra_steps: list[int]) -> None:
    steps = [_step(d) for d in sorted(extra_steps[:6])]
    with pytest.raises(ValueError):
        EscalationRule(
            id=uuid.uuid4(), user_id=uuid.uuid4(), name="Too many",
            deadline_type="fiscale", steps=steps,
        )
