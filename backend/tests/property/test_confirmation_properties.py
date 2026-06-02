"""Property-based tests for ConfirmationFlowService."""
from __future__ import annotations

from unittest.mock import AsyncMock

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.services.confirmation_flow_service import ACTION_RISK_LEVELS, ConfirmationFlowService


@given(st.sampled_from(list(ACTION_RISK_LEVELS.keys()) + ["unknown_action"]))
@settings(max_examples=15)
def test_risk_level_classification_consistent(action_type: str) -> None:
    service = ConfirmationFlowService(AsyncMock())
    level = service.classify_risk_level(action_type)
    if action_type in ACTION_RISK_LEVELS:
        assert level == ACTION_RISK_LEVELS[action_type]
    else:
        assert level == 2
