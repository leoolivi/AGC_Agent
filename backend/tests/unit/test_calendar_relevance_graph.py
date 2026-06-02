"""Unit tests for CalendarRelevanceGraph."""
from __future__ import annotations

import json

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.agent.graphs.calendar_relevance_graph import CalendarRelevanceGraph
from app.core.services.calendar_ingest_service import RELEVANCE_CONFIDENCE_THRESHOLD


RELEVANT_RESPONSE = json.dumps({
    "is_relevant": True,
    "confidence": 0.88,
    "suggested_category": "fiscale",
    "suggested_title": "Scadenza IVA Q1",
    "reasoning": "Evento fiscale",
})

IRRELEVANT_RESPONSE = json.dumps({
    "is_relevant": False,
    "confidence": 0.25,
    "suggested_category": "generico",
    "suggested_title": "Cena team",
    "reasoning": "Evento sociale",
})


class TestCalendarRelevanceGraph:
    @pytest.mark.asyncio
    async def test_relevant_event_above_threshold(self) -> None:
        graph = CalendarRelevanceGraph(DummyLLMAdapter(content=RELEVANT_RESPONSE))
        result = await graph.run({"title": "IVA Q1", "description": "Scadenza fiscale"})
        assert result["is_relevant"] is True
        assert result["confidence"] >= RELEVANCE_CONFIDENCE_THRESHOLD
        assert result["suggested_category"] == "fiscale"

    @pytest.mark.asyncio
    async def test_irrelevant_event_filtered(self) -> None:
        graph = CalendarRelevanceGraph(DummyLLMAdapter(content=IRRELEVANT_RESPONSE))
        result = await graph.run({"title": "Cena team"})
        assert result["is_relevant"] is False
        assert result["filtered_out"] is True

    @pytest.mark.asyncio
    async def test_category_suggestion(self) -> None:
        graph = CalendarRelevanceGraph(DummyLLMAdapter(content=RELEVANT_RESPONSE))
        result = await graph.run({"title": "IVA"})
        assert result["suggested_category"] == "fiscale"
        assert result["suggested_title"] == "Scadenza IVA Q1"

    @pytest.mark.asyncio
    async def test_fallback_keywords(self) -> None:
        graph = CalendarRelevanceGraph(DummyLLMAdapter(content="not json"))
        result = await graph.run({"title": "Scadenza IVA", "description": ""})
        assert result["is_relevant"] is True

    @pytest.mark.asyncio
    async def test_risk_score_read_only(self) -> None:
        graph = CalendarRelevanceGraph(DummyLLMAdapter(content=RELEVANT_RESPONSE))
        result = await graph.run({"title": "test"})
        assert result["risk_score"] == 0
