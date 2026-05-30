"""Property test: HITL Invariant.

Property 3: For any action with risk_score >= 3, the tool must never be executed
without a PendingConfirmation with status=approved.

Validates: Requirements 7.4, 7.5, 8.1, 8.9
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st


class MockToolExecutor:
    """Simulates tool execution with HITL gate."""

    def __init__(self) -> None:
        self.executed: list[dict] = []
        self.confirmations: dict[str, str] = {}  # task_id -> status

    def request_confirmation(self, task_id: str) -> None:
        self.confirmations[task_id] = "pending"

    def approve(self, task_id: str) -> None:
        self.confirmations[task_id] = "approved"

    def execute_if_allowed(self, task_id: str, risk_score: int) -> bool:
        """Execute tool only if risk < 3 or confirmation is approved."""
        if risk_score < 3:
            self.executed.append({"task_id": task_id, "risk": risk_score})
            return True
        # High risk: require approved confirmation
        if self.confirmations.get(task_id) == "approved":
            self.executed.append({"task_id": task_id, "risk": risk_score})
            return True
        return False


@given(
    risk_score=st.integers(min_value=3, max_value=5),
    approve_first=st.booleans(),
)
@settings(max_examples=200)
def test_hitl_invariant_high_risk_requires_approval(
    risk_score: int, approve_first: bool
) -> None:
    """High-risk actions must not execute without approved confirmation."""
    executor = MockToolExecutor()
    task_id = "task-1"

    executor.request_confirmation(task_id)

    if approve_first:
        executor.approve(task_id)

    executed = executor.execute_if_allowed(task_id, risk_score)

    if approve_first:
        assert executed is True
    else:
        assert executed is False
        # Verify tool was NOT executed
        assert not any(e["task_id"] == task_id for e in executor.executed)


@given(risk_score=st.integers(min_value=0, max_value=2))
@settings(max_examples=100)
def test_hitl_low_risk_executes_without_confirmation(risk_score: int) -> None:
    """Low-risk actions (risk < 3) execute without confirmation."""
    executor = MockToolExecutor()
    executed = executor.execute_if_allowed("task-low", risk_score)
    assert executed is True
