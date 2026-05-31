"""Atomic tools — each tool does ONE thing with a REAL effect in the DB.

The agent composes these dynamically based on the user's request.
Every tool returns a result dict and has observable side effects in the app.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Deadline, Document, EmailDraft, Notification
from app.db.session import build_session_factory

logger = structlog.get_logger()


async def _get_session() -> AsyncSession:
    factory = build_session_factory(settings.database_url)
    return factory()


# ─── Tool definitions (for the LLM prompt) ───

TOOL_DEFINITIONS = """
STRUMENTI DISPONIBILI (usa ESATTAMENTE questo formato, uno per riga):

1. TOOL: crea_scadenza | titolo | data_YYYY-MM-DD
   Effetto: crea una scadenza visibile nella pagina Scadenze (+ evento Google Calendar se collegato)
   Esempio: TOOL: crea_scadenza | Pagamento fattura Mario Tech | 2026-06-15

2. TOOL: crea_bozza_email | destinatario | oggetto | corpo_email
   Effetto: crea una bozza email visibile nella pagina Email
   Esempio: TOOL: crea_bozza_email | info@mariotech.it | Sollecito fattura INV-2026-047 | Gentile Mario Tech, vi ricordiamo che la fattura...

3. TOOL: crea_notifica | titolo | messaggio | livello(info/warning/urgent)
   Effetto: crea una notifica visibile nella campanella
   Esempio: TOOL: crea_notifica | Scadenza imminente | La fattura scade tra 3 giorni | warning

4. TOOL: cerca_documenti | query
   Effetto: nessuno (solo lettura), restituisce risultati di ricerca
   Esempio: TOOL: cerca_documenti | fatture mario tech

5. TOOL: leggi_email | query_opzionale
   Effetto: legge le ultime email dall'inbox Gmail dell'utente (richiede Google collegato)
   Esempio: TOOL: leggi_email | fattura

6. TOOL: importa_da_drive | nome_file_o_query
   Effetto: importa un file da Google Drive nel sistema (richiede Google collegato)
   Esempio: TOOL: importa_da_drive | contratto 2026

REGOLE:
- Puoi usare PIÙ tool nella stessa risposta (uno per riga)
- Rispondi PRIMA all'utente in modo conversazionale, POI aggiungi i TOOL: alla fine
- Usa i tool SOLO quando l'utente chiede di FARE qualcosa (non per domande informative)
- I dati che inserisci nei tool devono venire DAL CONTESTO, non inventati
"""


# ─── Tool executors ───

async def execute_tool(tool_line: str, user_id: str) -> str | None:
    """Parse and execute a single TOOL: line. Returns human-readable result."""
    try:
        raw = tool_line.replace("TOOL:", "").strip()
        parts = [p.strip() for p in raw.split("|")]
        tool_name = parts[0]

        if tool_name == "crea_scadenza":
            return await _create_deadline(user_id, parts)
        elif tool_name == "crea_bozza_email":
            return await _create_email_draft(user_id, parts)
        elif tool_name == "crea_notifica":
            return await _create_notification(user_id, parts)
        elif tool_name == "cerca_documenti":
            return await _search_documents(user_id, parts)
        elif tool_name == "leggi_email":
            return await _read_gmail(user_id, parts)
        elif tool_name == "importa_da_drive":
            return await _import_from_drive(user_id, parts)
        else:
            return f"Tool sconosciuto: {tool_name}"
    except Exception as e:
        logger.error("tool_execution_error", error=str(e), tool_line=tool_line)
        return f"Errore: {e}"


async def _create_deadline(user_id: str, parts: list[str]) -> str:
    """Create a real deadline in the DB. Also creates Calendar event if Google connected."""
    title = parts[1] if len(parts) > 1 else "Scadenza senza titolo"
    due_str = parts[2] if len(parts) > 2 else ""

    try:
        due = date.fromisoformat(due_str)
    except ValueError:
        return f"Data non valida: '{due_str}'. Formato richiesto: YYYY-MM-DD"

    async with await _get_session() as session:
        dl = Deadline(
            user_id=uuid.UUID(user_id),
            title=title,
            due_date=due,
            deadline_type="custom",
            source="ai_agent",
            status="active",
        )
        session.add(dl)
        await session.commit()

    # Try to create Google Calendar event
    calendar_note = ""
    try:
        from app.adapters.google import GoogleTokenStore
        store = GoogleTokenStore()
        if await store.has_valid_token(user_id, "google", "https://www.googleapis.com/auth/calendar.events"):
            from app.adapters.google.calendar_adapter import GoogleCalendarRealAdapter
            from app.core.ports.calendar import CalendarEvent
            cal = GoogleCalendarRealAdapter()
            event = CalendarEvent(title=title, due_datetime=datetime.combine(due, datetime.min.time()), description=f"Scadenza ACG: {title}")
            await cal.create_event(event, user_id)
            calendar_note = " + 📆 evento Google Calendar"
    except Exception:
        pass

    logger.info("tool_deadline_created", title=title, due_date=due_str)
    return f"📅 Scadenza creata: **{title}** → {due_str}{calendar_note}"


async def _create_email_draft(user_id: str, parts: list[str]) -> str:
    """Create a real email draft in the DB."""
    to = parts[1] if len(parts) > 1 else ""
    subject = parts[2] if len(parts) > 2 else "Senza oggetto"
    body = parts[3] if len(parts) > 3 else ""

    if not to:
        return "Destinatario mancante per la bozza email"

    # Clean up escaped newlines from LLM output
    body = body.replace("\\n", "\n").strip()

    # Convert markdown body to HTML for sending
    import re
    html_body = body
    html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
    html_body = re.sub(r'^\- (.+)$', r'<li>\1</li>', html_body, flags=re.MULTILINE)
    html_body = html_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html_body = f"<p>{html_body}</p>"
    html_body = html_body.replace("<p><li>", "<ul><li>").replace("</li></p>", "</li></ul>")

    async with await _get_session() as session:
        draft = EmailDraft(
            user_id=uuid.UUID(user_id),
            to_addresses=[a.strip() for a in to.split(",")],
            subject=subject,
            body_html=html_body,
            body_text=body,
            status="pending_review",
        )
        session.add(draft)
        await session.commit()

    logger.info("tool_email_draft_created", to=to, subject=subject)
    return f"✉️ Bozza email creata: **{subject}** → {to} (visibile in Email)"


async def _create_notification(user_id: str, parts: list[str]) -> str:
    """Create a real notification in the DB."""
    title = parts[1] if len(parts) > 1 else "Notifica"
    body = parts[2] if len(parts) > 2 else ""
    level = parts[3] if len(parts) > 3 else "info"

    if level not in ("info", "warning", "urgent", "action"):
        level = "info"

    async with await _get_session() as session:
        notif = Notification(
            user_id=uuid.UUID(user_id),
            title=title,
            body=body,
            level=level,
        )
        session.add(notif)
        await session.commit()

    logger.info("tool_notification_created", title=title, level=level)
    return f"🔔 Notifica creata: **{title}** [{level}]"


async def _search_documents(user_id: str, parts: list[str]) -> str:
    """Search documents by filename/type."""
    query = parts[1] if len(parts) > 1 else ""

    async with await _get_session() as session:
        result = await session.execute(
            select(Document.filename, Document.document_type, Document.id)
            .where(Document.user_id == uuid.UUID(user_id))
            .where(Document.filename.ilike(f"%{query}%") | Document.document_type.ilike(f"%{query}%"))
            .limit(5)
        )
        docs = result.all()

    if not docs:
        return f"Nessun documento trovato per '{query}'"
    return "Documenti trovati: " + ", ".join(f"{d[0]} ({d[1] or '?'})" for d in docs)


async def _read_gmail(user_id: str, parts: list[str]) -> str:
    """Read recent emails from Gmail."""
    query = parts[1] if len(parts) > 1 else ""
    try:
        from app.adapters.google import GoogleTokenStore
        store = GoogleTokenStore()
        if not await store.has_valid_token(user_id, "google", "https://www.googleapis.com/auth/gmail.readonly"):
            return "⚠️ Google non collegato. Vai in Impostazioni per collegare il tuo account."

        from app.adapters.google.gmail_adapter import GmailReaderAdapter
        reader = GmailReaderAdapter()
        emails = await reader.fetch_messages(user_id, max_results=5, query=query)
        if not emails:
            return "📭 Nessuna email trovata" + (f" per '{query}'" if query else "")
        lines = [f"📬 Ultime {len(emails)} email:"]
        for e in emails:
            lines.append(f"- **{e['subject']}** da {e['from']} — {e['snippet'][:60]}...")
        return "\n".join(lines)
    except Exception as e:
        return f"Errore lettura Gmail: {e}"


async def _import_from_drive(user_id: str, parts: list[str]) -> str:
    """Import a file from Google Drive."""
    query = parts[1] if len(parts) > 1 else ""
    if not query:
        return "Specifica il nome del file da importare da Drive"
    try:
        from app.adapters.google import GoogleTokenStore
        store = GoogleTokenStore()
        if not await store.has_valid_token(user_id, "google", "https://www.googleapis.com/auth/drive.readonly"):
            return "⚠️ Google non collegato. Vai in Impostazioni per collegare il tuo account."

        from app.adapters.google.drive_adapter import GoogleDriveAdapter
        drive = GoogleDriveAdapter()
        files = await drive.list_files(user_id, query=query, max_results=1)
        if not files:
            return f"Nessun file trovato su Drive per '{query}'"

        file_info = files[0]
        result = await drive.import_to_acg(user_id, file_info["id"])
        return f"📁 Importato da Drive: **{result['filename']}** ({result['size_bytes']} bytes) — ora visibile in Documenti"
    except Exception as e:
        return f"Errore importazione Drive: {e}"
