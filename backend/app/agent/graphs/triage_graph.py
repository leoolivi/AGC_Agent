"""TriageGraph — linear sequence for DOCUMENT_UPLOADED events.

Nodes: load_context → analyze_event → generate_options → classify_urgency → write_inbox_item
Risk score: max 1 (read + internal write only).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from app.core.ports.llm import LLMProviderPort

logger = structlog.get_logger()

URGENCY_RANK = {"immediate": 0, "today": 1, "this_week": 2, "low": 3}


class TriageGraph:
    """Linear triage graph for DOCUMENT_UPLOADED events."""

    def __init__(self, llm: LLMProviderPort) -> None:
        self._llm = llm

    async def run(self, event: dict, context: dict | None = None) -> dict:
        """Execute triage pipeline. Returns inbox item dict."""
        ctx = await self._load_context(event, context or {})
        analysis = await self._analyze_event(event, ctx)
        options = await self._generate_options(event, analysis)
        urgency = await self._classify_urgency(event, analysis)
        inbox_item = self._write_inbox_item(event, analysis, options, urgency)
        return inbox_item

    async def _load_context(self, event: dict, context: dict) -> dict:
        """Load related documents, deadlines, recent inbox items (max 10 each)."""
        return {
            "event_type": event.get("event_type", "DOCUMENT_UPLOADED"),
            "related_documents": context.get("related_documents", [])[:10],
            "active_deadlines": context.get("active_deadlines", [])[:10],
            "recent_inbox": context.get("recent_inbox", [])[:10],
        }

    async def _analyze_event(self, event: dict, context: dict) -> str:
        """LLM analyzes event + context."""
        payload = event.get("payload", {})
        filename = event.get("filename", "documento")
        doc_type = payload.get("document_type", "sconosciuto")
        fields = payload.get("extracted_fields", {})

        fields_summary = ", ".join(
            f"{k}: {v.get('value', '?')}" for k, v in fields.items()
            if isinstance(v, dict) and v.get("value") and v.get("confidence", 0) > 0.5
        ) if fields else "nessun campo estratto"

        prompt = (
            f"Un documento è stato caricato. Scrivi un'analisi breve (max 160 caratteri) per l'utente.\n"
            f"File: {filename}\nTipo: {doc_type}\nCampi estratti: {fields_summary}\n"
            f"Rispondi SOLO con il testo dell'analisi, senza virgolette."
        )
        try:
            resp = await self._llm.generate(prompt, system="Sei un assistente amministrativo conciso. Rispondi in italiano.")
            return resp.content.strip()[:200]
        except Exception as e:
            logger.warning("triage_analyze_failed", error=str(e))
            return f"Nuovo documento caricato: {filename} (tipo: {doc_type})"

    async def _generate_options(self, event: dict, analysis: str) -> list[dict]:
        """Generate 2-3 suggested actions. Always includes 'Nessuna azione / Archivia'."""
        prompt = (
            f"Dato questo evento e analisi, suggerisci 2-3 azioni possibili.\n"
            f"Analisi: {analysis}\nEvento: {json.dumps(event, default=str)}\n"
            f"Rispondi con JSON: {{\"actions\": [{{\"id\": \"...\", \"label\": \"...\", \"workflow_id\": \"...\"}}]}}"
        )
        try:
            resp = await self._llm.generate(prompt, system="Sei un assistente amministrativo.")
            data = json.loads(resp.content)
            actions = data.get("actions", [])[:2]
        except Exception:
            actions = []

        # Always include dismiss option
        actions.append({"id": "dismiss", "label": "Nessuna azione / Archivia", "workflow_id": None})
        return actions[:3]

    async def _classify_urgency(self, event: dict, analysis: str) -> str:
        """Classify urgency. Hard-coded rules first, LLM for ambiguous cases."""
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})

        # Hard-coded rules by event type
        if event_type == "DEADLINE_OVERDUE":
            return "immediate"
        if event_type == "DEADLINE_APPROACHING":
            days = payload.get("days_until", 999)
            if days <= 1:
                return "immediate"
            if days <= 7:
                return "today"
            return "this_week"

        deadline_str = payload.get("deadline") or payload.get("data_scadenza")
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(str(deadline_str))
                now = datetime.now(timezone.utc)
                days_until = (deadline - now).days
                if days_until < 1:
                    return "immediate"
                if days_until < 7:
                    return "today"
            except (ValueError, TypeError):
                pass

        if payload.get("days_overdue", 0) > 30:
            return "immediate"

        if event_type == "EMAIL_RECEIVED":
            return "today"

        # LLM fallback for ambiguous cases
        prompt = (
            f"Classifica l'urgenza di questo evento: immediate, today, this_week, low.\n"
            f"Analisi: {analysis}\nRispondi con una sola parola."
        )
        try:
            resp = await self._llm.generate(prompt, system="Classifica urgenza.")
            urgency = resp.content.strip().lower()
            if urgency in URGENCY_RANK:
                return urgency
        except Exception:
            pass

        # Deterministic fallback
        return "this_week"

    def _write_inbox_item(
        self, event: dict, analysis: str, options: list[dict], urgency: str
    ) -> dict:
        """Compose AgentInboxItem dict."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": event.get("user_id", ""),
            "event_type": event.get("event_type", "DOCUMENT_UPLOADED"),
            "event_source": event,
            "source_ref_id": event.get("document_id"),
            "agent_analysis": analysis,
            "urgency": urgency,
            "suggested_actions": options,
            "status": "pending",
            "risk_score": 1,
        }
