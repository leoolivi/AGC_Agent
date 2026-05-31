"""ChatAgentGraph — structured agent with tool calling.

Architecture (inspired by OpenAI Assistants / Anthropic tool_use):
1. Context is loaded as structured data, not raw text dump
2. LLM responds conversationally OR calls a tool — never both mixed
3. Tool definitions are explicit with typed parameters
4. Two-pass: first generate response, then check if tool call is needed
"""
from __future__ import annotations

import json
import uuid as _uuid

import structlog
from sqlalchemy import select

from app.agent.guardrails.guardrail_layer import GuardrailLayer
from app.agent.workflows.registry import WorkflowTemplateRegistry
from app.config import settings
from app.core.ports.llm import LLMProviderPort
from app.db.models import AgentInbox, Deadline, Document, DocumentChunk
from app.db.session import build_session_factory

logger = structlog.get_logger()

# Compact system prompt — no JSON instructions, just behavior
SYSTEM_PROMPT = """Sei ACG, l'assistente amministrativo dell'azienda. L'utente è il proprietario/amministratore.

COMPORTAMENTO:
- Rispondi in italiano, conciso e professionale
- Hai accesso completo ai documenti dell'utente: mostra QUALSIASI dato richiesto (IBAN, importi, P.IVA, ecc.)
- Basa le risposte SOLO sui dati nel contesto. Se un'informazione non è presente, dillo chiaramente
- Ogni documento è un'entità separata: specifica sempre la fonte ("Dalla fattura X...")
- Distingui FATTI (dati nel documento) da AZIONI (cose da fare). Non trasformare clausole in azioni
- NON inventare date, importi o scadenze non presenti nei documenti
- Usa markdown per formattare (tabelle, grassetto, liste)

STRUMENTI DISPONIBILI:
Se l'utente chiede di ESEGUIRE un'azione (non solo informazioni), rispondi con ESATTAMENTE questo formato su una riga separata alla fine:
TOOL_CALL: nome_tool | argomento

Strumenti:
- sollecito_pagamento | nome_file_fattura → prepara bozza email di sollecito
- crea_scadenza | titolo, data → crea una scadenza nel sistema
- processa_documento | nome_file → rielabora classificazione ed estrazione
- report_pagamenti | (nessun arg) → genera report stato pagamenti

Usa TOOL_CALL solo quando l'utente chiede ESPLICITAMENTE di fare qualcosa. Per domande informative, rispondi normalmente."""


# Tool definitions with resolver logic
TOOLS = {
    "sollecito_pagamento": {"workflow": "draft_payment_reminder", "resolve": "fattura"},
    "crea_scadenza": {"workflow": "create_deadline_from_document", "resolve": "any"},
    "processa_documento": {"workflow": "process_document", "resolve": "any"},
    "report_pagamenti": {"workflow": "generate_payment_status_report", "resolve": None},
}


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
        """Process message: guardrail → context → LLM → tool extraction → response."""
        # 1. Input guardrail
        check = self._guardrails.check_input(message)
        if not check.allowed:
            return {"response": check.reason, "blocked": True}

        # 2. Load structured context
        context = await self._build_context(user_id)

        # 3. Generate LLM response
        user_prompt = f"{context}\n\n---\nMESSAGGIO UTENTE: {message}"
        try:
            resp = await self._llm.generate(user_prompt, system=SYSTEM_PROMPT)
            content = resp.content.strip()
        except Exception as e:
            logger.error("chat_llm_error", error=str(e))
            return {"response": "Errore di comunicazione con il modello. Riprova.", "blocked": False}

        # 4. Extract tool call if present
        tool_result = None
        response_text = content
        if "TOOL_CALL:" in content:
            lines = content.split("\n")
            tool_lines = [l for l in lines if l.strip().startswith("TOOL_CALL:")]
            response_lines = [l for l in lines if not l.strip().startswith("TOOL_CALL:")]
            response_text = "\n".join(response_lines).strip()

            for tool_line in tool_lines:
                tool_result = await self._execute_tool(tool_line, user_id)
                if tool_result:
                    response_text += f"\n\n✅ {tool_result}"

        # 5. Output guardrail
        out_check = self._guardrails.check_output(response_text)
        if not out_check.allowed:
            return {"response": "Non posso rispondere a questa richiesta.", "blocked": True}

        return {"response": response_text, "workflow_id": None, "blocked": False}

    async def _execute_tool(self, tool_line: str, user_id: str) -> str | None:
        """Parse and execute a TOOL_CALL line."""
        try:
            # Format: "TOOL_CALL: tool_name | arg"
            parts = tool_line.replace("TOOL_CALL:", "").strip().split("|")
            tool_name = parts[0].strip()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if tool_name not in TOOLS:
                return None

            tool_def = TOOLS[tool_name]
            workflow_id = tool_def["workflow"]

            # Resolve document_id
            args = await self._resolve_document(arg, user_id, tool_def.get("resolve"))

            # Execute workflow
            from app.agent.graphs.workflow_graph import WorkflowGraph
            from app.agent.risk.engine import RiskEngine

            wg = WorkflowGraph(registry=self._registry, risk_engine=RiskEngine(), llm=self._llm)
            template = self._registry.get(workflow_id)
            valid_keys = set(template.required_args + template.optional_args)
            clean_args = {k: v for k, v in args.items() if k in valid_keys}
            result = await wg.run(workflow_id, clean_args, user_id)

            done = [s for s in result["steps"] if s["status"] == "done"]
            waiting = [s for s in result["steps"] if s["status"] == "waiting_confirmation"]
            summary = f"Workflow '{tool_name}' completato: {len(done)} step eseguiti"
            if waiting:
                summary += f", {len(waiting)} in attesa di conferma"
            return summary
        except Exception as e:
            logger.warning("tool_execution_failed", error=str(e), tool_line=tool_line)
            return f"Errore nell'esecuzione: {e}"

    async def _resolve_document(self, hint: str, user_id: str, resolve_type: str | None) -> dict:
        """Resolve a filename hint to a document_id."""
        if not resolve_type:
            return {}
        try:
            factory = build_session_factory(settings.database_url)
            async with factory() as session:
                query = select(Document.id).where(Document.user_id == _uuid.UUID(user_id))
                if hint:
                    query = query.where(Document.filename.ilike(f"%{hint}%"))
                elif resolve_type == "fattura":
                    query = query.where(Document.document_type == "fattura")
                row = (await session.execute(
                    query.order_by(Document.created_at.desc()).limit(1)
                )).first()
                if row:
                    return {"document_id": str(row[0])}
        except Exception:
            pass
        return {}

    async def _build_context(self, user_id: str) -> str:
        """Build compact, structured context for the LLM."""
        try:
            factory = build_session_factory(settings.database_url)
            async with factory() as session:
                uid = _uuid.UUID(user_id)

                # Documents with metadata
                docs = (await session.execute(
                    select(Document).where(Document.user_id == uid)
                    .order_by(Document.created_at.desc()).limit(10)
                )).scalars().all()

                # Deadlines
                deadlines = (await session.execute(
                    select(Deadline).where(Deadline.user_id == uid, Deadline.status == "active")
                    .order_by(Deadline.due_date).limit(10)
                )).scalars().all()

                # Inbox
                inbox = (await session.execute(
                    select(AgentInbox).where(AgentInbox.user_id == uid, AgentInbox.status == "pending")
                    .order_by(AgentInbox.created_at.desc()).limit(5)
                )).scalars().all()

            sections: list[str] = []

            # Documents section — structured per document
            if docs:
                sections.append("## DOCUMENTI")
                for d in docs:
                    meta = d.extracted_metadata or {}
                    fields = {k: v.get("value") for k, v in meta.items()
                              if isinstance(v, dict) and v.get("value")
                              and str(v.get("value")) not in ("-", "", "N/D", "None")}
                    sections.append(f"\n### {d.filename}")
                    sections.append(f"- ID: {d.id}")
                    sections.append(f"- Tipo: {d.document_type or 'non classificato'}")
                    sections.append(f"- Stato: {d.parse_status}")
                    if fields:
                        sections.append("- Campi estratti:")
                        for k, v in fields.items():
                            sections.append(f"  - {k}: {v}")

                # Full text for top 3 docs
                async with factory() as session:
                    for d in docs[:3]:
                        chunks = (await session.execute(
                            select(DocumentChunk.content)
                            .where(DocumentChunk.document_id == d.id)
                            .order_by(DocumentChunk.chunk_index).limit(4)
                        )).all()
                        if chunks:
                            text = "\n".join(r[0] for r in chunks)[:2500]
                            sections.append(f"\n**Testo di {d.filename}:**\n{text}")
                        else:
                            # Read from storage
                            try:
                                from app.adapters.parsers.pymupdf_parser import PyMuPDFParser
                                from app.api.deps import get_storage
                                storage = get_storage()
                                data = await storage.get(str(d.id))
                                parser = PyMuPDFParser()
                                if parser.can_parse(d.content_type, d.filename):
                                    parsed = await parser.parse(data, d.filename)
                                    sections.append(f"\n**Testo di {d.filename}:**\n{parsed.text[:2500]}")
                            except Exception:
                                pass

            # Deadlines section
            if deadlines:
                sections.append("\n## SCADENZE ATTIVE")
                for d in deadlines:
                    sections.append(f"- **{d.title}** → {d.due_date} ({d.deadline_type}, fonte: {d.source})")

            # Inbox section
            if inbox:
                sections.append("\n## INBOX PENDENTI")
                for i in inbox:
                    sections.append(f"- [{i.urgency}] {i.agent_analysis[:120]}")

            if not sections:
                return "Nessun documento, scadenza o elemento inbox presente nel sistema."

            return "\n".join(sections)
        except Exception as e:
            logger.warning("context_build_failed", error=str(e))
            return "Errore nel caricamento del contesto."
