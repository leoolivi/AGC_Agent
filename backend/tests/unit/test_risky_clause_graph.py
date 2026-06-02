"""Unit tests for RiskyClauseGraph."""
from __future__ import annotations

import json
import uuid

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.agent.graphs.risky_clause_graph import RiskyClauseGraph


CLAUSE_RESPONSE = json.dumps({
    "clauses": [
        {
            "category": "rinnovo_automatico",
            "severity": "alto",
            "clause_text": "Il contratto si rinnova tacitamente per ulteriori 12 mesi.",
            "page_number": 2,
            "paragraph_ref": "Art. 8",
            "plain_language_explanation": "Il contratto si rinnova da solo se non disdetti.",
            "confidence_score": 0.91,
        },
        {
            "category": "penale",
            "severity": "medio",
            "clause_text": "Penale del 10% per ritardo nei pagamenti.",
            "page_number": 5,
            "paragraph_ref": "Art. 12",
            "plain_language_explanation": "Ritardo pagamenti costa il 10%.",
            "confidence_score": 0.82,
        },
    ]
})


@pytest.fixture
def graph() -> RiskyClauseGraph:
    llm = DummyLLMAdapter(content=CLAUSE_RESPONSE)
    return RiskyClauseGraph(llm=llm, clause_service=None)


class TestRiskyClauseGraph:
    @pytest.mark.asyncio
    async def test_category_detection(self, graph: RiskyClauseGraph) -> None:
        result = await graph.run(str(uuid.uuid4()), "Contratto con rinnovo automatico...", persist=False)
        categories = {c["category"] for c in result["clauses"]}
        assert "rinnovo_automatico" in categories
        assert "penale" in categories

    @pytest.mark.asyncio
    async def test_severity_assignment(self, graph: RiskyClauseGraph) -> None:
        result = await graph.run(str(uuid.uuid4()), "test", persist=False)
        severities = {c["severity"] for c in result["clauses"]}
        assert "alto" in severities
        assert "medio" in severities

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, graph: RiskyClauseGraph) -> None:
        result = await graph.run(str(uuid.uuid4()), "test", persist=False)
        for clause in result["clauses"]:
            assert 0.0 <= clause["confidence_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_plain_language_generation(self, graph: RiskyClauseGraph) -> None:
        result = await graph.run(str(uuid.uuid4()), "test", persist=False)
        for clause in result["clauses"]:
            assert len(clause["plain_language_explanation"]) <= 200
            assert clause["plain_language_explanation"]

    @pytest.mark.asyncio
    async def test_risk_score_read_only(self, graph: RiskyClauseGraph) -> None:
        result = await graph.run(str(uuid.uuid4()), "test", persist=False)
        assert result["risk_score"] == 0
