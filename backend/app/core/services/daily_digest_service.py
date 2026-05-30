"""DailyDigestService — generates morning briefing for users."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import structlog

logger = structlog.get_logger()

DIGEST_TEMPLATE = """## Buongiorno! Ecco il tuo riepilogo.

### ⚠️ Attenzione immediata
{immediate}

### 📋 Da fare questa settimana
{this_week}

### 📁 Tutto il resto
{rest}

### 💡 Suggerimento del giorno
{tip}
"""


class DailyDigestService:
    """Generates daily digest for users. Phase 3: LLM-powered pattern detection."""

    def __init__(self, llm=None) -> None:
        self._llm = llm

    async def generate_for_user(self, user_id: str, situation: dict) -> dict:
        """Generate digest for a single user from collected situation data."""
        try:
            digest_text = self._compose_digest(situation)
            return {
                "user_id": user_id,
                "digest": digest_text,
                "event_type": "daily_digest",
                "urgency": "immediate",
                "status": "ok",
            }
        except Exception as e:
            logger.error("digest_generation_failed", user_id=user_id, error=str(e))
            return {"user_id": user_id, "status": "error", "error": str(e)}

    async def generate_for_all_users(self, users: list[dict]) -> list[dict]:
        """Generate digest for all users. Error on one doesn't block others."""
        results: list[dict] = []
        for user in users:
            situation = self._collect_situation(user)
            result = await self.generate_for_user(user["id"], situation)
            results.append(result)
        return results

    def _collect_situation(self, user: dict) -> dict:
        """Collect situation data from DB (stub for Phase 2)."""
        return {
            "overdue_deadlines": user.get("overdue_deadlines", []),
            "urgent_deadlines": user.get("urgent_deadlines", []),
            "week_deadlines": user.get("week_deadlines", []),
            "pending_reviews": user.get("pending_reviews", 0),
            "pending_drafts": user.get("pending_drafts", 0),
            "stale_inbox": user.get("stale_inbox", 0),
        }

    def _compose_digest(self, situation: dict) -> str:
        overdue = situation.get("overdue_deadlines", [])
        urgent = situation.get("urgent_deadlines", [])
        week = situation.get("week_deadlines", [])

        immediate = "\n".join(f"- {d}" for d in overdue + urgent) or "Nessuna urgenza."
        this_week = "\n".join(f"- {d}" for d in week) or "Nessuna scadenza questa settimana."

        rest_items: list[str] = []
        if situation.get("pending_reviews"):
            rest_items.append(f"- {situation['pending_reviews']} conferme in attesa")
        if situation.get("pending_drafts"):
            rest_items.append(f"- {situation['pending_drafts']} bozze email da revisionare")
        if situation.get("stale_inbox"):
            rest_items.append(f"- {situation['stale_inbox']} elementi inbox non risolti da >48h")
        rest = "\n".join(rest_items) or "Tutto in ordine."

        tip = "Ricorda di controllare le fatture in scadenza questa settimana."

        return DIGEST_TEMPLATE.format(
            immediate=immediate, this_week=this_week, rest=rest, tip=tip
        )

    async def detect_patterns(self, situation: dict) -> str:
        """Use LLM to detect anomalous patterns. Max 1 suggestion, max 200 tokens."""
        if not self._llm:
            return "Ricorda di controllare le fatture in scadenza questa settimana."
        prompt = (
            f"Analizza questa situazione aziendale e identifica UN pattern anomalo o suggerimento proattivo (max 200 token).\n"
            f"Scadenze scadute: {situation.get('overdue_deadlines', [])}\n"
            f"Scadenze urgenti: {situation.get('urgent_deadlines', [])}\n"
            f"Conferme pendenti: {situation.get('pending_reviews', 0)}\n"
            f"Inbox stale >48h: {situation.get('stale_inbox', 0)}\n"
            f"Rispondi con UN solo suggerimento conciso in italiano."
        )
        try:
            resp = await self._llm.generate(prompt, system="Sei un analista amministrativo.")
            return resp.content.strip()[:200]
        except Exception:
            return "Ricorda di controllare le fatture in scadenza questa settimana."
