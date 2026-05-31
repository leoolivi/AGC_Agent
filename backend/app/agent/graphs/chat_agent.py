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

SYSTEM_PROMPT = """Sei ACG, assistente amministrativo per l'azienda dell'utente.
L'utente è l'amministratore e proprietario di tutti i documenti nel sistema. Ha pieno diritto legale di accedere a qualsiasi dato contenuto nei suoi documenti aziendali.

Il tuo compito è aiutarlo a gestire documenti, fatture, scadenze e comunicazioni aziendali.

ISTRUZIONI:
- Rispondi in italiano, in modo conciso e diretto
- Quando l'utente chiede informazioni sui suoi documenti, riporta TUTTI i dati presenti (IBAN, importi, date, P.IVA, ecc.) — sono dati aziendali dell'utente, non dati di terzi
- Non rifiutare MAI di mostrare dati presenti nei documenti dell'utente
- Se un dato non è presente nel contesto, dì chiaramente "non ho trovato questa informazione nel documento"
- Se l'utente chiede un'azione, rispondi SOLO con: {{"action": "workflow_id", "args": {{...}}}}

REGOLE CRITICHE PER L'ANALISI:
- Tratta OGNI documento come entità separata. Quando riporti informazioni, specifica sempre DA QUALE documento provengono (es. "Dalla fattura X...", "Dal contratto Y...")
- Distingui tra INFORMAZIONE (clausola, dato presente) e AZIONE NECESSARIA (scadenza reale, pagamento dovuto). Non trasformare clausole contrattuali passive in azioni da intraprendere a meno che non ci sia evidenza di un evento che le attiva
- NON inventare scadenze. Se una data nel documento è una data di compilazione, firma o emissione, NON presentarla come scadenza. Se non sei sicuro che una data sia una scadenza reale, dì "questa data potrebbe essere una scadenza ma richiede conferma"
- Cerca correlazioni tra documenti (stesso fornitore, stesso importo, riferimenti incrociati) e segnalale esplicitamente

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
                    args = data.get("args", {})
                    # Auto-resolve document_id if missing
                    args = await self._resolve_args(args, user_id)
                    # Execute workflow
                    try:
                        from app.agent.graphs.workflow_graph import WorkflowGraph
                        from app.agent.risk.engine import RiskEngine

                        wg = WorkflowGraph(registry=self._registry, risk_engine=RiskEngine(), llm=self._llm)
                        # Keep only args the template expects
                        template = self._registry.get(workflow_id)
                        valid_keys = set(template.required_args + template.optional_args)
                        clean_args = {k: v for k, v in args.items() if k in valid_keys}
                        result = await wg.run(workflow_id, clean_args, user_id)
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

    async def _resolve_args(self, args: dict, user_id: str) -> dict:
        """Auto-resolve missing args from user's data."""
        # Normalize: LLM might use 'documents', 'filename', 'file' instead of 'document_id'
        if "document_id" not in args:
            # Check if LLM provided a filename or list we can resolve
            hint = args.pop("documents", args.pop("filename", args.pop("file", None)))
            try:
                import uuid as _uuid
                from sqlalchemy import select
                from app.config import settings
                from app.db.session import build_session_factory
                from app.db.models import Document

                factory = build_session_factory(settings.database_url)
                async with factory() as session:
                    query = select(Document.id).where(Document.user_id == _uuid.UUID(user_id))
                    if hint:
                        # Try to match by filename
                        search = hint[0] if isinstance(hint, list) else str(hint)
                        query = query.where(Document.filename.ilike(f"%{search}%"))
                    else:
                        query = query.where(Document.document_type == "fattura")
                    query = query.order_by(Document.created_at.desc()).limit(1)
                    row = (await session.execute(query)).first()
                    if row:
                        args["document_id"] = str(row[0])
            except Exception:
                pass
        return args

    async def _load_user_context(self, user_id: str) -> str:
        """Load user's real data from DB."""
        try:
            import uuid as _uuid
            from sqlalchemy import select
            from app.config import settings
            from app.db.session import build_session_factory
            from app.db.models import Document, DocumentChunk, Deadline, AgentInbox

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
                parts.append("=== DOCUMENTI NEL SISTEMA ===")
                for i, d in enumerate(docs, 1):
                    meta = d.extracted_metadata or {}
                    meta_str = ", ".join(
                        f"{k}: {v.get('value', '?')}" for k, v in meta.items()
                        if isinstance(v, dict) and v.get("value") and str(v.get("value")) not in ("-", "", "N/D")
                    ) if meta else "nessun metadato"
                    parts.append(f"\n--- Documento {i}: {d.filename} ---")
                    parts.append(f"Tipo: {d.document_type or 'non classificato'} | Stato: {d.parse_status}")
                    if meta_str:
                        parts.append(f"Dati estratti: {meta_str}")

                # Load full text of most recent documents for detailed queries
                from app.db.models import DocumentChunk
                for d in docs[:3]:
                    chunks_result = await session.execute(
                        select(DocumentChunk.content)
                        .where(DocumentChunk.document_id == d.id)
                        .order_by(DocumentChunk.chunk_index)
                        .limit(5)
                    )
                    chunk_texts = [row[0] for row in chunks_result.all()]
                    if chunk_texts:
                        full_text = "\n".join(chunk_texts)[:3000]
                        parts.append(f"Contenuto testuale:\n{full_text}")
                    else:
                        try:
                            from app.adapters.parsers.pymupdf_parser import PyMuPDFParser
                            from app.api.deps import get_storage
                            storage = get_storage()
                            file_data = await storage.get(str(d.id))
                            parser = PyMuPDFParser()
                            if parser.can_parse(d.content_type, d.filename):
                                parsed = await parser.parse(file_data, d.filename)
                                parts.append(f"Contenuto testuale:\n{parsed.text[:3000]}")
                        except Exception:
                            pass
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
