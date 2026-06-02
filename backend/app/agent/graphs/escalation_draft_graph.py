"""EscalationDraftGraph — generates email/calendar drafts for escalation steps."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import structlog

from app.core.ports.llm import LLMProviderPort

logger = structlog.get_logger()

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "escalation_draft.md"


class EscalationDraftGraph:
    """Generate escalation drafts. Risk score 0 (draft only)."""

    RISK_SCORE = 0

    def __init__(self, llm: LLMProviderPort) -> None:
        self._llm = llm
        self._system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    async def run(
        self,
        deadline: dict[str, Any],
        channel: Literal["email", "calendar"],
        message_template: str,
        recipient: str = "",
        source_document: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = {
            "deadline": deadline,
            "channel": channel,
            "message_template": message_template,
            "recipient": recipient,
            "source_document": source_document,
        }
        prompt = f"Genera bozza escalation:\n{json.dumps(context, ensure_ascii=False, default=str)}"

        try:
            resp = await self._llm.generate(prompt=prompt, system=self._system_prompt)
            draft = json.loads(resp.content)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("escalation_draft_failed", error=str(e))
            draft = self._fallback_draft(deadline, channel, message_template, recipient)

        draft["channel"] = channel
        draft["risk_score"] = self.RISK_SCORE
        return draft

    def _fallback_draft(
        self,
        deadline: dict[str, Any],
        channel: Literal["email", "calendar"],
        message_template: str,
        recipient: str,
    ) -> dict[str, Any]:
        title = deadline.get("title", "Scadenza")
        due = deadline.get("due_date", "")
        body = message_template.format(deadline_title=title, due_date=due)

        if channel == "email":
            return {
                "channel": "email",
                "subject": f"Promemoria: {title}",
                "body_text": body,
                "body_html": f"<p>{body}</p>",
                "recipient": recipient,
            }
        return {
            "channel": "calendar",
            "title": f"Promemoria: {title}",
            "description": body,
            "start_datetime": f"{due}T09:00:00",
            "duration_minutes": 30,
        }
