"""ChatAgentGraph — agent with atomic tools that have real DB effects.

The agent doesn't have pre-defined workflows. It has atomic tools and
composes them dynamically based on the user's request. Results are
immediately visible in the app (email-drafts, deadlines, notifications).
"""
from __future__ import annotations

import uuid as _uuid

import structlog
from sqlalchemy import select

from app.agent.guardrails.guardrail_layer import GuardrailLayer
from app.agent.tools.atomic import TOOL_DEFINITIONS, execute_tool
from app.config import settings
from app.core.ports.llm import LLMProviderPort
from app.db.models import AgentInbox, Deadline, Document, DocumentChunk
from app.db.session import build_session_factory

logger = structlog.get_logger()

SYSTEM_PROMPT = """Sei ACG, l'assistente amministrativo dell'azienda. L'utente è il proprietario/amministratore.

COMPORTAMENTO:
- Rispondi in italiano, conciso e professionale, usa markdown
- Hai accesso completo ai documenti dell'utente: mostra QUALSIASI dato richiesto (IBAN, importi, P.IVA)
- Basa le risposte SOLO sui dati nel contesto. Se un'informazione non c'è, dillo
- Ogni documento è un'entità separata: specifica sempre la fonte
- NON inventare dati, date o importi non presenti nel contesto
- Distingui FATTI (dati presenti) da AZIONI (cose da fare realmente)

{tools}"""


class ChatAgentGraph:
    def __init__(
        self,
        llm: LLMProviderPort,
        guardrails: GuardrailLayer,
        **_kwargs,  # Accept registry for backward compat
    ) -> None:
        self._llm = llm
        self._guardrails = guardrails

    async def handle_message(self, message: str, user_id: str, session_id: str) -> dict:
        """Process message → context → LLM → extract & execute tools → response."""
        # 1. Guardrail
        check = self._guardrails.check_input(message)
        if not check.allowed:
            return {"response": check.reason, "blocked": True}

        # 2. Build context
        context = await self._build_context(user_id)

        # 3. LLM call
        system = SYSTEM_PROMPT.format(tools=TOOL_DEFINITIONS)
        user_prompt = f"{context}\n\n---\nUTENTE: {message}"

        try:
            resp = await self._llm.generate(user_prompt, system=system)
            content = resp.content.strip()
        except Exception as e:
            logger.error("chat_llm_error", error=str(e))
            return {"response": "Errore di comunicazione con il modello. Riprova.", "blocked": False}

        # 4. Extract and execute TOOL: lines
        lines = content.split("\n")
        response_lines: list[str] = []
        tool_results: list[str] = []

        for line in lines:
            if line.strip().startswith("TOOL:"):
                result = await execute_tool(line.strip(), user_id)
                if result:
                    tool_results.append(result)
            else:
                response_lines.append(line)

        response_text = "\n".join(response_lines).strip()
        if tool_results:
            response_text += "\n\n---\n**Azioni eseguite:**\n" + "\n".join(f"- {r}" for r in tool_results)

        # 5. Output guardrail
        out_check = self._guardrails.check_output(response_text)
        if not out_check.allowed:
            return {"response": "Non posso rispondere a questa richiesta.", "blocked": True}

        return {"response": response_text, "workflow_id": None, "blocked": False}

    async def _build_context(self, user_id: str) -> str:
        """Build compact structured context with priority for Google Drive files."""
        try:
            factory = build_session_factory(settings.database_url)
            uid = _uuid.UUID(user_id)

            async with factory() as session:
                # 1. Fetch Google Drive documents (up to 7)
                drive_docs = (await session.execute(
                    select(Document).where(Document.user_id == uid, Document.source == "drive")
                    .order_by(Document.created_at.desc()).limit(7)
                )).scalars().all()

                # 2. Fetch other recent documents
                other_docs = (await session.execute(
                    select(Document).where(Document.user_id == uid, Document.source != "drive")
                    .order_by(Document.created_at.desc()).limit(10 - len(drive_docs))
                )).scalars().all()

                docs = list(drive_docs) + list(other_docs)

                deadlines = (await session.execute(
                    select(Deadline).where(Deadline.user_id == uid, Deadline.status == "active")
                    .order_by(Deadline.due_date).limit(10)
                )).scalars().all()

                inbox = (await session.execute(
                    select(AgentInbox).where(AgentInbox.user_id == uid, AgentInbox.status == "pending")
                    .order_by(AgentInbox.created_at.desc()).limit(5)
                )).scalars().all()

            sections: list[str] = []

            # Documents
            if docs:
                sections.append("## DOCUMENTI (Priorità: Google Drive)")
                for d in docs:
                    meta = d.extracted_metadata or {}
                    fields = {k: v.get("value") for k, v in meta.items()
                              if isinstance(v, dict) and v.get("value")
                              and str(v.get("value")) not in ("-", "", "N/D", "None")}
                    source_label = "[GOOGLE DRIVE]" if d.source == "drive" else "[CARICATO]"
                    sections.append(f"\n### {source_label} {d.filename} (tipo: {d.document_type or '?'}, stato: {d.parse_status})")
                    if fields:
                        for k, v in fields.items():
                            sections.append(f"- {k}: {v}")

                # Full text top 4 (prioritizing drive)
                async with factory() as session:
                    for d in docs[:4]:
                        chunks = (await session.execute(
                            select(DocumentChunk.content)
                            .where(DocumentChunk.document_id == d.id)
                            .order_by(DocumentChunk.chunk_index).limit(4)
                        )).all()
                        if chunks:
                            sections.append(f"\nTesto {d.filename}:\n" + "\n".join(r[0] for r in chunks)[:3000])
                        else:
                            try:
                                from app.adapters.parsers.pymupdf_parser import PyMuPDFParser
                                from app.api.deps import get_storage
                                storage = get_storage()
                                data = await storage.get(str(d.id))
                                parser = PyMuPDFParser()
                                if parser.can_parse(d.content_type, d.filename):
                                    parsed = await parser.parse(data, d.filename)
                                    sections.append(f"\nTesto {d.filename}:\n{parsed.text[:3000]}")
                            except Exception:
                                pass

            # Deadlines
            if deadlines:
                sections.append("\n## SCADENZE ATTIVE")
                for d in deadlines:
                    sections.append(f"- **{d.title}** → {d.due_date} (fonte: {d.source})")

            # Inbox
            if inbox:
                sections.append("\n## INBOX")
                for i in inbox:
                    sections.append(f"- [{i.urgency}] {i.agent_analysis[:120]}")

            return "\n".join(sections) if sections else "Nessun dato nel sistema."
        except Exception as e:
            logger.warning("context_build_failed", error=str(e))
            return "Errore nel caricamento del contesto."
