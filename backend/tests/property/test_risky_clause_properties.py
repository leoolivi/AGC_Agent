"""Property-based tests for RiskyClauseService."""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.services.risky_clause_service import CONFIDENCE_THRESHOLD_UNCERTAIN, SEVERITY_ORDER


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
@settings(max_examples=30)
def test_confidence_threshold_classification(score: float) -> None:
    is_uncertain = score < CONFIDENCE_THRESHOLD_UNCERTAIN
    if score >= 0.75:
        assert not is_uncertain
    elif score < 0.75:
        assert is_uncertain


def test_severity_ordering_invariant() -> None:
    assert SEVERITY_ORDER["alto"] < SEVERITY_ORDER["medio"] < SEVERITY_ORDER["basso"]
