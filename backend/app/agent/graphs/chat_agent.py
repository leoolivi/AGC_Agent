"""ChatAgentGraph — conversational agent with real context.

No rigid intent mapping. The LLM gets full context and decides how to respond.
"""
from __future__ import annotations

import json
import uuid

import structlog

from app.agent.guardrails.guardrail_layer import GuardrailLayer
from app.agent.workflows.registry import WorkflowTemplateRegistry
from app.core.ports.llm import LLMProviderPort

logger = structlog.get_logger()

SYSTEM_PROMPT = """Sei ACG, un assistente amministrativo intelligente per PMI italiane.
Hai accesso ai documenti, scadenze e inbox dell'utente.

Regole:
- Rispondi SEMPRE in italiano
- Sii conciso e diretto
- Se l'utente chiede di fare un'azione (inviare sollecito, creare scadenza, ecc.), rispondi con JSON: {"action": "workflow_id", "args": {...}}
- Per tutto il resto, rispondi in modo conversazionale e utile
- Se hai dati dell'utente nel contesto, usali per rispondere
- Non inventare dati che non hai

Workflow disponibili:
{workflows}"""


class ChatAgentGraph:
    def __init__(
        self,
        llm: LLMProviderPort,
        registry: WorkflowTemplateRegistry,
        guardrails: GuardrailLayer,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._guardrails = guardrails

    async def handle_message(self, message: str, user_id: str, session_id: str) -> dict:
        """Process user message with full context."""
        # Guardrail check
        check = self._guardrails.check_input(message)
        if not check.allowed:
            return {"response": check.reason, "blocked": True}

        # Load context
        context = await self._load_user_context(user_id)

        # Build system prompt with workflows
        workflows_desc = "\n".join(
            f"- {t.workflow_id}: {t.description}" for t in self._registry.list_all()
        )
        system = SYSTEM_PROMPT.format(workflows=workflows_desc)

        # Build user message with context
        user_prompt = f"Contesto attuale dell'utente:\n{context}\n\nMessaggio dell'utente: {message}"

        # Generate response
        try:
            resp = await self._llm.generate(user_prompt, system=system)
            content = resp.content.strip()
        except Exception as e:
            logger.error("chat_agent_llm_error", error=str(e))
            return {"response": "Mi dispiace, si è verificato un errore. Riprova.", "blocked": False}

        # Check if response contains an action
        workflow_id = None
        if "{" in content and '"action"' in content:
            try:
                json_start = content.index("{")
                json_end = content.rindex("}") + 1
                data = json.loads(content[json_start:json_end])
                if data.get("action"):
                    workflow_id = data["action"]
                    # Execute workflow
                    try:
                        from app.agent.graphs.workflow_graph import WorkflowGraph
                        from app.agent.risk.engine import RiskEngine

                        wg = WorkflowGraph(registry=self._registry, risk_engine=RiskEngine(), llm=self._llm)
                        result = await wg.run(workflow_id, data.get("args", {}), user_id)
                        steps = ", ".join(f"{s['tool']} ({s['status']})" for s in result["steps"])
                        return {
                            "response": f"Ho eseguito '{workflow_id}': {steps}",
                            "workflow_id": workflow_id,
                            "blocked": False,
                        }
                    except ValueError as e:
                        return {"response": str(e), "workflow_id": workflow_id, "blocked": False}
            except (json.JSONDecodeError, ValueError):
                pass

        # Output guardrail
        out_check = self._guardrails.check_output(content)
        if not out_check.allowed:
            return {"response": "Non posso rispondere a questa richiesta.", "blocked": True}

        return {"response": content, "workflow_id": workflow_id, "blocked": False}

    async def _load_user_context(self, user_id: str) -> str:
        """Load user's real data from DB."""
        try:
            import uuid as _uuid
            from sqlalchemy import select
            from app.config import settings
            from app.db.session import build_session_factory
            from app.db.models import Document, Deadline, AgentInbox

            factory = build_session_factory(settings.database_url)
            async with factory() as session:
                docs = (await session.execute(
                    select(Document)
                    .where(Document.user_id == _uuid.UUID(user_id))
                    .order_by(Document.created_at.desc()).limit(10)
                )).scalars().all()

                deadlines = (await session.execute(
                    select(Deadline)
                    .where(Deadline.user_id == _uuid.UUID(user_id))
                    .where(Deadline.status == "active")
                    .order_by(Deadline.due_date).limit(10)
                )).scalars().all()

                inbox = (await session.execute(
                    select(AgentInbox)
                    .where(AgentInbox.user_id == _uuid.UUID(user_id))
                    .where(AgentInbox.status == "pending")
                    .order_by(AgentInbox.created_at.desc()).limit(5)
                )).scalars().all()

            parts: list[str] = []
            if docs:
                parts.append("DOCUMENTI:")
                for d in docs:
                    meta = d.extracted_metadata or {}
                    parts.append(f"  - {d.filename} | tipo: {d.document_type or '?'} | stato: {d.parse_status} | metadati: {json.dumps(meta, default=str)[:200]}")
            else:
                parts.append("DOCUMENTI: nessuno")

            if deadlines:
                parts.append("SCADENZE ATTIVE:")
                for d in deadlines:
                    parts.append(f"  - {d.title} | scadenza: {d.due_date} | tipo: {d.deadline_type}")
            else:
                parts.append("SCADENZE: nessuna")

            if inbox:
                parts.append("INBOX PENDENTI:")
                for i in inbox:
                    parts.append(f"  - [{i.urgency}] {i.agent_analysis[:100]}")
            else:
                parts.append("INBOX: vuota")

            return "\n".join(parts)
        except Exception as e:
            logger.warning("context_load_failed", error=str(e))
            return "Contesto non disponibile."
