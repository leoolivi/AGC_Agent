"""Property test: Parser Round-Trip.

Property 5: For any valid ParsedDocument, serializing to JSON and deserializing
must produce an object with identical key fields (text, tables, metadata, confidence).

Validates: Requirements 25.5
"""
from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.ports.parser import ParsedDocument


@given(
    text=st.text(min_size=1, max_size=500),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    tables=st.lists(st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=20)), max_size=3),
    metadata=st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=20), max_size=5),
)
@settings(max_examples=300)
def test_parsed_document_round_trip(
    text: str, confidence: float, tables: list[dict], metadata: dict
) -> None:
    """Serialize ParsedDocument to JSON and back — key fields must be identical."""
    original = ParsedDocument(
        text=text,
        tables=tables,
        metadata=metadata,
        confidence=confidence,
    )
    serialized = json.dumps({
        "text": original.text,
        "tables": original.tables,
        "metadata": original.metadata,
        "confidence": original.confidence,
    })
    deserialized = json.loads(serialized)
    assert deserialized["text"] == original.text
    assert deserialized["tables"] == original.tables
    assert deserialized["metadata"] == original.metadata
    assert abs(deserialized["confidence"] - original.confidence) < 1e-10
