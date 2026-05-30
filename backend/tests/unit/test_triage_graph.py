"""Unit tests for TriageGraph."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.agent.graphs.triage_graph import TriageGraph


@pytest.fixture
def triage_graph() -> TriageGraph:
    llm = DummyLLMAdapter(content=json.dumps({"actions": [{"id": "a1", "label": "Crea scadenza", "workflow_id": "create_deadline"}]}))
    return TriageGraph(llm=llm)


@pytest.fixture
def doc_event() -> dict:
    return {
        "event_type": "DOCUMENT_UPLOADED",
        "user_id": "user-1",
        "document_id": "doc-1",
        "filename": "Fattura_2024.pdf",
        "payload": {},
    }


class TestTriageGraph:
    @pytest.mark.asyncio
    async def test_full_sequence(self, triage_graph: TriageGraph, doc_event: dict) -> None:
        result = await triage_graph.run(doc_event)
        assert result["event_type"] == "DOCUMENT_UPLOADED"
        assert result["user_id"] == "user-1"
        assert result["status"] == "pending"
        assert result["urgency"] in ("immediate", "today", "this_week", "low")
        assert len(result["suggested_actions"]) <= 3

    @pytest.mark.asyncio
    async def test_always_includes_dismiss(self, triage_graph: TriageGraph, doc_event: dict) -> None:
        result = await triage_graph.run(doc_event)
        labels = [a["label"] for a in result["suggested_actions"]]
        assert "Nessuna azione / Archivia" in labels

    @pytest.mark.asyncio
    async def test_max_3_actions(self, triage_graph: TriageGraph, doc_event: dict) -> None:
        result = await triage_graph.run(doc_event)
        assert len(result["suggested_actions"]) <= 3

    @pytest.mark.asyncio
    async def test_urgency_immediate_deadline_24h(self) -> None:
        llm = DummyLLMAdapter(content=json.dumps({"actions": []}))
        graph = TriageGraph(llm=llm)
        tomorrow = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        event = {
            "event_type": "DOCUMENT_UPLOADED",
            "user_id": "u1",
            "payload": {"deadline": tomorrow},
        }
        result = await graph.run(event)
        assert result["urgency"] == "immediate"

    @pytest.mark.asyncio
    async def test_urgency_today_within_7_days(self) -> None:
        llm = DummyLLMAdapter(content=json.dumps({"actions": []}))
        graph = TriageGraph(llm=llm)
        in_5_days = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        event = {
            "event_type": "DOCUMENT_UPLOADED",
            "user_id": "u1",
            "payload": {"deadline": in_5_days},
        }
        result = await graph.run(event)
        assert result["urgency"] == "today"

    @pytest.mark.asyncio
    async def test_urgency_immediate_overdue_30_days(self) -> None:
        llm = DummyLLMAdapter(content=json.dumps({"actions": []}))
        graph = TriageGraph(llm=llm)
        event = {
            "event_type": "DOCUMENT_UPLOADED",
            "user_id": "u1",
            "payload": {"days_overdue": 35},
        }
        result = await graph.run(event)
        assert result["urgency"] == "immediate"

    @pytest.mark.asyncio
    async def test_fallback_urgency_this_week(self) -> None:
        """If LLM fails, urgency defaults to this_week."""
        class FailingLLM(DummyLLMAdapter):
            async def generate(self, prompt, system, context=None):
                raise RuntimeError("LLM down")

        graph = TriageGraph(llm=FailingLLM())
        event = {"event_type": "DOCUMENT_UPLOADED", "user_id": "u1", "payload": {}}
        result = await graph.run(event)
        assert result["urgency"] == "this_week"

    @pytest.mark.asyncio
    async def test_risk_score_max_1(self, triage_graph: TriageGraph, doc_event: dict) -> None:
        result = await triage_graph.run(doc_event)
        assert result["risk_score"] <= 1
