"""Unit tests for EscalationDraftGraph."""
from __future__ import annotations

import json

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.agent.graphs.escalation_draft_graph import EscalationDraftGraph

EMAIL_DRAFT = json.dumps({
    "channel": "email",
    "subject": "Promemoria: IVA Q1",
    "body_text": "La scadenza IVA Q1 è imminente.",
    "body_html": "<p>La scadenza IVA Q1 è imminente.</p>",
    "recipient": "admin@example.com",
})

CALENDAR_DRAFT = json.dumps({
    "channel": "calendar",
    "title": "Promemoria: Contratto fornitore",
    "description": "Rinnovo contratto in scadenza",
    "start_datetime": "2026-06-01T09:00:00",
    "duration_minutes": 30,
})

DEADLINE = {"title": "IVA Q1", "due_date": "2026-04-16", "deadline_type": "fiscale"}


class TestEscalationDraftGraph:
    @pytest.mark.asyncio
    async def test_email_draft_generation(self) -> None:
        graph = EscalationDraftGraph(DummyLLMAdapter(content=EMAIL_DRAFT))
        result = await graph.run(
            deadline=DEADLINE,
            channel="email",
            message_template="Reminder: {deadline_title} due {due_date}",
            recipient="admin@example.com",
        )
        assert result["channel"] == "email"
        assert "subject" in result
        assert "body_text" in result

    @pytest.mark.asyncio
    async def test_calendar_draft_generation(self) -> None:
        graph = EscalationDraftGraph(DummyLLMAdapter(content=CALENDAR_DRAFT))
        result = await graph.run(
            deadline={"title": "Contratto", "due_date": "2026-06-01"},
            channel="calendar",
            message_template="Rinnovo {deadline_title}",
        )
        assert result["channel"] == "calendar"
        assert "title" in result
        assert "start_datetime" in result

    @pytest.mark.asyncio
    async def test_fallback_email(self) -> None:
        graph = EscalationDraftGraph(DummyLLMAdapter(content="invalid"))
        result = await graph.run(
            deadline=DEADLINE,
            channel="email",
            message_template="Reminder: {deadline_title}",
            recipient="a@b.com",
        )
        assert result["channel"] == "email"
        assert result["recipient"] == "a@b.com"

    @pytest.mark.asyncio
    async def test_risk_score_draft_only(self) -> None:
        graph = EscalationDraftGraph(DummyLLMAdapter(content=EMAIL_DRAFT))
        result = await graph.run(DEADLINE, "email", "msg")
        assert result["risk_score"] == 0
