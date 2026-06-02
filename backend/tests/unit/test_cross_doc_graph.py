"""Unit tests for CrossDocGraph."""
from __future__ import annotations

import json
import uuid

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.agent.graphs.cross_doc_graph import CrossDocGraph

TARGET_ID = str(uuid.uuid4())

CORRELATION_RESPONSE = json.dumps({
    "correlations": [
        {
            "target_document_id": TARGET_ID,
            "correlation_type": "derivato_da",
            "confidence_score": 0.88,
            "source_passage": "Rif. ordine n. 123",
            "target_passage": "Ordine n. 123",
        },
        {
            "target_document_id": str(uuid.uuid4()),
            "correlation_type": "in_conflitto_con",
            "confidence_score": 0.79,
            "source_passage": "Importo 1000 EUR",
            "target_passage": "Importo 1500 EUR",
        },
    ]
})


@pytest.fixture
def graph() -> CrossDocGraph:
    llm = DummyLLMAdapter(content=CORRELATION_RESPONSE)
    return CrossDocGraph(llm=llm, cross_doc_service=None)


class TestCrossDocGraph:
    @pytest.mark.asyncio
    async def test_correlation_type_classification(self, graph: CrossDocGraph) -> None:
        result = await graph.run(
            user_id=str(uuid.uuid4()),
            source_document_id=str(uuid.uuid4()),
            source_text="Fattura rif. ordine n. 123",
            candidate_documents=[{"id": TARGET_ID, "filename": "ordine.pdf", "text": "Ordine n. 123"}],
            persist=False,
        )
        types = {c["correlation_type"] for c in result["correlations"]}
        assert "derivato_da" in types
        assert "in_conflitto_con" in types

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, graph: CrossDocGraph) -> None:
        result = await graph.run(
            user_id=str(uuid.uuid4()),
            source_document_id=str(uuid.uuid4()),
            source_text="test",
            candidate_documents=[{"id": TARGET_ID, "filename": "a.pdf"}],
            persist=False,
        )
        for corr in result["correlations"]:
            assert 0.0 <= corr["confidence_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_conflict_detection(self, graph: CrossDocGraph) -> None:
        result = await graph.run(
            user_id=str(uuid.uuid4()),
            source_document_id=str(uuid.uuid4()),
            source_text="test",
            candidate_documents=[{"id": TARGET_ID, "filename": "a.pdf"}],
            persist=False,
        )
        assert len(result["conflicts"]) >= 1
        assert result["conflicts"][0]["correlation_type"] == "in_conflitto_con"

    @pytest.mark.asyncio
    async def test_risk_score_internal_write(self, graph: CrossDocGraph) -> None:
        result = await graph.run(
            user_id=str(uuid.uuid4()),
            source_document_id=str(uuid.uuid4()),
            source_text="test",
            candidate_documents=[],
            persist=False,
        )
        assert result["risk_score"] == 1
