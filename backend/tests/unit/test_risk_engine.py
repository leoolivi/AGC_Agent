"""Property-based test: Risk Score Monotonicity.

Property 1: For any valid tool_name and any subset of context modifiers,
compute_risk() must return a value in [risk_base, 5]; adding modifiers
cannot lower the risk score.

Validates: Requirements 7.2, 7.7
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.agent.risk.engine import PlannedAction, RiskEngine

engine = RiskEngine()

valid_tools = list(engine.tool_risk_base.keys())
valid_modifiers = list(engine.context_modifiers.keys())


@given(
    tool=st.sampled_from(valid_tools),
    modifiers=st.lists(st.sampled_from(valid_modifiers), max_size=len(valid_modifiers)),
)
@settings(max_examples=500)
def test_risk_score_in_valid_range(tool: str, modifiers: list[str]) -> None:
    """Risk score must be in [risk_base, 5]."""
    action = PlannedAction(tool_name=tool, context_flags=modifiers)
    score = engine.compute_risk(action)
    base = engine.tool_risk_base[tool]
    assert base <= score <= 5, f"score={score} not in [{base}, 5] for {tool} with {modifiers}"


@given(
    tool=st.sampled_from(valid_tools),
    modifiers=st.lists(st.sampled_from(valid_modifiers), min_size=0, max_size=len(valid_modifiers)),
)
@settings(max_examples=500)
def test_risk_score_monotonicity(tool: str, modifiers: list[str]) -> None:
    """Adding modifiers cannot lower the risk score."""
    for i in range(len(modifiers)):
        subset = modifiers[:i]
        superset = modifiers[: i + 1]
        score_subset = engine.compute_risk(PlannedAction(tool_name=tool, context_flags=subset))
        score_superset = engine.compute_risk(PlannedAction(tool_name=tool, context_flags=superset))
        assert score_superset >= score_subset, (
            f"Adding modifier {modifiers[i]} lowered score from {score_subset} to {score_superset}"
        )
