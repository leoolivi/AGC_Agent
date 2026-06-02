"""CalendarRelevanceGraph — classifies calendar events for administrative relevance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from app.core.ports.llm import LLMProviderPort
from app.core.services.calendar_ingest_service import RELEVANCE_CONFIDENCE_THRESHOLD

logger = structlog.get_logger()

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "calendar_relevance.md"


class CalendarRelevanceGraph:
    """Classify calendar event relevance. Risk score 0 (read-only)."""

    RISK_SCORE = 0

    def __init__(self, llm: LLMProviderPort) -> None:
        self._llm = llm
        self._system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    async def run(self, event: dict[str, Any]) -> dict[str, Any]:
        title = event.get("title", event.get("summary", ""))
        description = event.get("description", "")
        participants = event.get("participants", event.get("attendees", []))
        start = event.get("start", "")

        prompt = (
            f"Titolo: {title}\n"
            f"Descrizione: {description}\n"
            f"Partecipanti: {participants}\n"
            f"Data: {start}\n"
            "Classifica la rilevanza amministrativa."
        )

        try:
            resp = await self._llm.generate(prompt=prompt, system=self._system_prompt)
            data = json.loads(resp.content)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("calendar_relevance_parse_failed", error=str(e))
            data = self._fallback_classify(title, description)

        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        is_relevant = bool(data.get("is_relevant", False)) and confidence >= RELEVANCE_CONFIDENCE_THRESHOLD

        return {
            "is_relevant": is_relevant,
            "confidence": confidence,
            "suggested_category": data.get("suggested_category", "generico"),
            "suggested_title": data.get("suggested_title", title),
            "reasoning": data.get("reasoning", ""),
            "risk_score": self.RISK_SCORE,
            "filtered_out": not is_relevant,
        }

    def _fallback_classify(self, title: str, description: str) -> dict[str, Any]:
        text = f"{title} {description}".lower()
        keywords = ["iva", "f24", "scadenza", "pagamento", "contratto", "fiscale", "tribut"]
        if any(k in text for k in keywords):
            return {
                "is_relevant": True,
                "confidence": 0.75,
                "suggested_category": "fiscale" if "iva" in text or "f24" in text else "generico",
                "suggested_title": title,
                "reasoning": "Rilevate parole chiave amministrative",
            }
        return {
            "is_relevant": False,
            "confidence": 0.30,
            "suggested_category": "generico",
            "suggested_title": title,
            "reasoning": "Nessun indicatore amministrativo",
        }
