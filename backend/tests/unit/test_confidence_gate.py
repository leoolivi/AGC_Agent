"""Property test: Confidence Gate Completeness.

Property 2: For any list of fields with confidence scores, the number of
PendingConfirmation items must equal the number of fields with confidence < threshold.
No below-threshold field can be saved without PendingConfirmation.

Validates: Requirements 5.9, 6.1, 6.2
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.agent.risk.engine import RiskEngine
from app.core.services.confidence_gate import evaluate_confidence

engine = RiskEngine()


@given(
    confidences=st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=1, max_size=20),
)
@settings(max_examples=500)
def test_confidence_gate_completeness(confidences: list[float]) -> None:
    """Number of pending fields must equal fields below threshold."""
    # Build fields dict with generic field names
    fields = {
        f"field_{i}": {"value": f"val_{i}", "confidence": c}
        for i, c in enumerate(confidences)
    }

    result = evaluate_confidence(
        fields=fields,
        document_type_confidence=0.95,  # above threshold, so only fields matter
        risk_engine=engine,
        user_id="test-user",
        document_type="fattura",
    )

    # Count fields below threshold
    threshold = engine.get_threshold("field_extraction")  # 0.85 for generic fields
    expected_pending = sum(1 for c in confidences if c < threshold)
    expected_accepted = sum(1 for c in confidences if c >= threshold)

    assert len(result.pending_fields) == expected_pending
    assert len(result.accepted_fields) == expected_accepted

    # No below-threshold field in accepted
    for field_name, field_data in result.accepted_fields.items():
        assert field_data["confidence"] >= threshold


@given(
    doc_confidence=st.floats(min_value=0.0, max_value=0.79, allow_nan=False),
)
@settings(max_examples=100)
def test_low_doc_confidence_creates_pending(doc_confidence: float) -> None:
    """If document_type_confidence < 0.80, a pending field for document_type is created."""
    result = evaluate_confidence(
        fields={},
        document_type_confidence=doc_confidence,
        risk_engine=engine,
        user_id="test-user",
        document_type="altro",
    )
    doc_type_pending = [p for p in result.pending_fields if p["field_name"] == "document_type"]
    assert len(doc_type_pending) == 1
    assert result.group_id is not None
