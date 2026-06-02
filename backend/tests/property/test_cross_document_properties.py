"""Property-based tests for CrossDocumentService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.domain.correlation import DocumentCorrelation
from app.core.services.cross_document_service import CrossDocumentService


@given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
@settings(max_examples=30)
def test_correlation_visibility_thresholds(score: float) -> None:
    service = CrossDocumentService(AsyncMock())
    corr = DocumentCorrelation(
        id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        target_document_id=uuid.uuid4(),
        correlation_type="derivato_da",
        confidence_score=score,
    )
    level = service.classify_confidence(corr)
    if score >= 0.85:
        assert level == "certain"
    elif score >= 0.60:
        assert level == "probable"
    else:
        assert level == "hidden"


def test_different_docs_constraint() -> None:
    doc_id = uuid.uuid4()
    with pytest.raises(ValueError):
        DocumentCorrelation(
            id=uuid.uuid4(),
            source_document_id=doc_id,
            target_document_id=doc_id,
            correlation_type="derivato_da",
            confidence_score=0.8,
        )
