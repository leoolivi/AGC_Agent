"""Tests for Trust Progressivo — effective_threshold adjusts with accuracy."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agent.risk.engine import RiskEngine

engine = RiskEngine()


class TestEffectiveThreshold:
    def test_no_accuracy_returns_base(self) -> None:
        result = engine.effective_threshold("u1", "fattura", "field_extraction", accuracy=None)
        assert result == engine.get_threshold("field_extraction")

    def test_low_accuracy_returns_base(self) -> None:
        result = engine.effective_threshold("u1", "fattura", "field_extraction", accuracy=0.5)
        assert result == engine.get_threshold("field_extraction")

    def test_high_accuracy_lowers_threshold(self) -> None:
        base = engine.get_threshold("field_extraction")
        result = engine.effective_threshold("u1", "fattura", "field_extraction", accuracy=0.95)
        assert result < base

    def test_perfect_accuracy_max_reduction(self) -> None:
        base = engine.get_threshold("field_extraction")
        result = engine.effective_threshold("u1", "fattura", "field_extraction", accuracy=1.0)
        assert result == base - 0.15

    def test_threshold_never_below_half(self) -> None:
        result = engine.effective_threshold("u1", "fattura", "field_extraction", accuracy=1.0)
        assert result >= 0.5

    @given(accuracy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=200)
    def test_threshold_monotonically_decreases_with_accuracy(self, accuracy: float) -> None:
        """Higher accuracy should never increase the threshold."""
        base = engine.get_threshold("field_extraction")
        result = engine.effective_threshold("u1", "fattura", "field_extraction", accuracy=accuracy)
        assert result <= base
        assert result >= 0.5
