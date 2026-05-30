# Design Document — Admin & Compliance Guardian MVP (`acg-mvp`)

## Overview

L'**Admin & Compliance Guardian (ACG)** è un assistente amministrativo AI per PMI italiane. Il sistema monitora proattivamente documenti, scadenze e comunicazioni aziendali, analizza ogni evento in arrivo e presenta all'utente situazioni già elaborate con opzioni d'azione pre-compilate.

Il paradigma UX primario è l'**Agent Inbox**: l'agente non aspetta domande, ma analizza eventi (upload documenti, scadenze in arrivo, email ricevute) e produce card azionabili con verb specifici. La chat è una feature avanzata, non il punto di ingresso principale.

**Principio guida: Reliability > Autonomy.** Il sistema esegue il massimo lavoro possibile in autonomia, ma richiede sempre approvazione umana esplicita per ogni azione con effetti esterni.

### Stack Tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph, SQLAlchemy (async), Alembic |
| Database | PostgreSQL 16 + pgvector |
| File Storage | Local (dev) / MinIO (self-hosted) / S3 (cloud) |
| LLM | Anthropic Claude (primary), OpenAI GPT-4o, Google Gemini 1.5 Pro |
| Document Parsing | LlamaParse (PDF), Unstructured.io (PDF fallback + XLS/XLSX), pandas (CSV) |
| Frontend | React 19, TypeScript, Vite, shadcn/ui, TailwindCSS, React Query, Zustand |
| Scheduler | APScheduler |
| Auth | JWT locale (bcrypt) o Clerk (cloud) |
| Logging | structlog (JSON strutturato) |
| Type checking | mypy --strict |

---

## Architecture

### Architettura Esagonale

Il sistema adotta un'architettura esagonale (ports & adapters). Il core business logic non dipende da nessuna implementazione concreta: ogni dipendenza esterna è accessibile solo tramite un `typing.Protocol` Python. Il wiring avviene esclusivamente in `app/api/deps.py` tramite variabili d'ambiente.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                                │
│   [REST API /api/v1/]    [File Upload]    [APScheduler]             │
└──────────┬──────────────────┬──────────────────────┬───────────────┘
           │                  │                      │
           ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│   DocumentService   DeadlineService   EmailDraftService             │
│   NotificationService   AuditService   DailyDigestService           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   AGENT CORE     │ │  STORAGE PORTS   │ │  EXTERNAL PORTS  │
│   (LangGraph)    │ │  FileStoragePort │ │  LLMProviderPort │
│   RiskEngine     │ │  VectorStorePort │ │  EmailSenderPort │
│   GuardrailLayer │ │  Database (ORM)  │ │  CalendarPort    │
└──────────────────┘ └──────────────────┘ └──────────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   ADAPTERS       │ │   ADAPTERS       │ │   ADAPTERS       │
│   LangGraph impl │ │   Local/MinIO/S3 │ │   Anthropic API  │
│                  │ │   pgvector       │ │   SMTP           │
│                  │ │                  │ │   [DEFERRED: n8n]│
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Tre Grafi LangGraph

Il cuore dell'agente è composto da tre grafi LangGraph con responsabilità distinte:

- **TriageGraph**: processa ogni evento in arrivo, produce un `AgentInboxItem`. Risk score massimo: 1. Non blocca mai su conferme.
- **WorkflowGraph**: esegue un'azione specifica avviata da inbox, chat o sistema (per risk ≤ 2).
- **DailyDigestGraph**: gira ogni mattina alle 08:00, produce il briefing giornaliero.

### Struttura Directory

```
acg/
├── backend/
│   ├── app/
│   │   ├── core/                      # Business logic pura, zero dipendenze esterne
│   │   │   ├── domain/                # Entità e value objects (Pydantic v2)
│   │   │   ├── ports/                 # Protocol definitions (interfaces)
│   │   │   └── services/              # Use cases
│   │   ├── agent/
│   │   │   ├── graphs/                # TriageGraph, WorkflowGraph, DailyDigestGraph
│   │   │   ├── nodes/                 # Singoli nodi LangGraph
│   │   │   ├── tools/                 # Tool registry
│   │   │   ├── risk/                  # RiskEngine + rules.yaml
│   │   │   ├── workflows/             # WorkflowTemplateRegistry + templates
│   │   │   ├── prompts/               # System prompt .md (mai hardcodati in Python)
│   │   │   └── guardrails/            # constitution.md, blacklist.yaml, GuardrailLayer
│   │   ├── adapters/
│   │   │   ├── storage/               # local, minio, s3
│   │   │   ├── llm/                   # anthropic, openai, gemini, fallback_chain
│   │   │   ├── parsers/               # pdf_parser, spreadsheet_parser
│   │   │   ├── email/                 # smtp_adapter
│   │   │   ├── calendar/              # google_calendar_adapter [DEFERRED stub TD-002]
│   │   │   ├── vector/                # pgvector_adapter
│   │   │   └── notifier/              # inapp_notifier, email_notifier
│   │   ├── api/v1/                    # FastAPI routers
│   │   ├── db/                        # SQLAlchemy models + Alembic migrations
│   │   ├── config.py
│   │   └── main.py
│   └── tests/
│       ├── unit/                      # Test core/ con mock dei port
│       └── integration/               # Test con adapter reali
├── frontend/src/
│   ├── pages/
│   ├── components/
│   ├── hooks/
│   ├── api/                           # Typed API client
│   └── store/                         # Zustand + React Query
├── docker-compose.yml
└── infra/env.example
```

---

## Components and Interfaces

### Core Ports

Ogni port è un `typing.Protocol`. Nessun `import` di adapter nel core. Il wiring avviene in `app/api/deps.py`.

```python
# app/core/ports/storage.py
from typing import Protocol, BinaryIO
from dataclasses import dataclass

@dataclass
class FileMetadata:
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    user_id: str

class FileStoragePort(Protocol):
    async def save(self, file: BinaryIO, filename: str, user_id: str, content_type: str) -> FileMetadata: ...
    async def get(self, file_id: str) -> bytes: ...
    async def delete(self, file_id: str) -> bool: ...
    async def list(self, user_id: str, prefix: str = "") -> list[FileMetadata]: ...
```

```python
# app/core/ports/llm.py
from typing import Protocol, AsyncIterator
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    model: str
    confidence: float | None  # None se il modello non lo espone
    raw: dict                  # Response grezza per debug

class LLMProviderPort(Protocol):
    async def generate(self, prompt: str, system: str, context: list[dict] | None = None) -> LLMResponse: ...
    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]: ...
```

```python
# app/core/ports/parser.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class ParsedDocument:
    text: str
    tables: list[dict]         # Tabelle estratte come strutture
    metadata: dict             # Titolo, date, autore se presenti
    raw_pages: list[str]       # Testo per pagina
    confidence: float          # 0.0-1.0: quanto è affidabile l'estrazione

class DocumentParserPort(Protocol):
    def can_parse(self, content_type: str, filename: str) -> bool: ...
    async def parse(self, file: bytes, filename: str) -> ParsedDocument: ...
```

```python
# app/core/ports/email.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body_html: str
    body_text: str
    reply_to: str | None = None

class EmailSenderPort(Protocol):
    async def send(self, message: EmailMessage) -> bool: ...
    async def send_draft(self, draft_id: str) -> bool: ...
```

```python
# app/core/ports/vector.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class VectorSearchResult:
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict

class VectorStorePort(Protocol):
    async def upsert(self, document_id: str, chunks: list[str], metadata: list[dict]) -> bool: ...
    async def search(self, query: str, user_id: str, top_k: int = 10) -> list[VectorSearchResult]: ...
    async def delete(self, document_id: str) -> bool: ...
```

```python
# app/core/ports/calendar.py
from typing import Protocol
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CalendarEvent:
    title: str
    due_datetime: datetime
    description: str
    external_id: str | None = None

class CalendarPort(Protocol):
    async def create_event(self, event: CalendarEvent, user_id: str) -> str: ...  # returns event_id
    async def delete_event(self, event_id: str, user_id: str) -> bool: ...
```

```python
# app/core/ports/notifier.py
from typing import Protocol

class NotifierPort(Protocol):
    async def send_inapp(self, user_id: str, title: str, body: str, level: str) -> bool: ...
    async def send_email_notification(self, user_id: str, subject: str, body: str) -> bool: ...
```

### RiskEngine

**Responsabilità:** calcola il risk score di ogni azione pianificata leggendo `app/agent/risk/rules.yaml`. Implementazione MVP basata su regole YAML, sostituibile con modello ML senza modificare l'interfaccia (`[TODO: TD-003]`).

**Dipendenze:** nessuna porta esterna — legge solo il file `rules.yaml` locale.

```python
# app/agent/risk/engine.py
from dataclasses import dataclass

@dataclass
class PlannedAction:
    tool_name: str
    args: dict
    context_flags: list[str]  # es. ["involves_external_party", "involves_monetary_amount"]

class RiskEngine:
    def compute_risk(self, action: PlannedAction, context: dict) -> int:
        """
        Calcola risk score finale: risk_base + sum(context_modifiers).
        Risultato sempre in [risk_base, 5].
        """
        ...

    def get_threshold(self, field_name: str) -> float:
        """
        Restituisce la soglia di confidence per un campo specifico da rules.yaml.
        Es: get_threshold("amount_extraction") -> 0.92
        """
        ...

    def effective_threshold(self, user_id: str, document_type: str, field_name: str) -> float:
        """
        Phase 3: abbassa la soglia base in proporzione all'accuracy storica dell'utente.
        Phase 0-2: restituisce get_threshold(field_name) senza leggere user_extraction_trust.
        """
        ...
```

### GuardrailLayer

**Responsabilità:** applica controlli di sicurezza a tre livelli (input, execution, output). Blocca richieste in blacklist, verifica la Constitution, valida il formato dell'output.

**Dipendenze:** `LLMProviderPort` (per classifier leggero), file `constitution.md` e `blacklist.yaml`.

```python
# app/agent/guardrails/guardrail_layer.py
from dataclasses import dataclass
from enum import Enum

class GuardrailStatus(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    REDACT = "redact"

@dataclass
class GuardrailResult:
    status: GuardrailStatus
    reason: str | None
    modified_content: str | None  # contenuto dopo redact, None se PASS o BLOCK

class GuardrailLayer:
    def check_input(self, message: str, user_id: str) -> GuardrailResult:
        """
        Livello 1: PII detection, jailbreak detection, blacklist check.
        Eseguito prima che l'agente veda il messaggio.
        """
        ...

    def check_output(self, output: str) -> GuardrailResult:
        """
        Livello 3: validazione formato (date ISO 8601, importi numerici, P.IVA),
        PII re-check, constitutional rules final check.
        """
        ...

    def check_action(self, action: PlannedAction) -> GuardrailResult:
        """
        Livello 2: verifica che l'azione non sia in blacklist e rispetti la Constitution.
        Eseguito durante LangGraph prima di ogni tool call.
        """
        ...
```

### TriageGraph

**Responsabilità:** processa ogni evento in arrivo e produce un `AgentInboxItem`. Non esegue azioni rischiose (risk score massimo: 1). Non blocca mai su conferme.

**Input:** `AgentEvent`
**Output:** `AgentInboxItem` scritto su DB + notifica in-app

**Nodi in sequenza:**

```
load_context → analyze_event → generate_options → classify_urgency → write_inbox_item
```

```python
# app/agent/graphs/triage_graph.py

# Nodo: load_context
# Carica dal DB: fino a 10 documenti correlati alla stessa entità, scadenze active,
# storico AgentInboxItem degli ultimi 90 giorni per la stessa entità.

# Nodo: analyze_event
# LLM analizza evento + contesto: cosa sta succedendo, azione implicita/esplicita,
# urgenza, entità coinvolte (importi, date, persone).

# Nodo: generate_options
# LLM genera 2-3 azioni suggerite ordinate per rilevanza.
# Per ogni azione: label human-readable, workflow_id, argomenti pre-compilati, risk_score stimato.
# Sempre inclusa l'opzione "Nessuna azione / Archivia". MAX 3 opzioni totali.

# Nodo: classify_urgency
# Regole hard-coded (non LLM) per determinismo:
#   deadline < 24h → immediate
#   pagamento scaduto > 30gg → immediate
#   deadline < 7gg → today
#   tutto il resto → this_week o low via LLM (fallback deterministico: this_week)

# Nodo: write_inbox_item
# Scrive AgentInboxItem su agent_inbox.
# Invia notifica: urgent se immediate, warning se today, info se this_week/low.
# Se scrittura fallisce: log audit, termina senza notifica.
```

### WorkflowGraph

**Responsabilità:** esegue una sequenza di azioni specifiche. Avviato da scelta utente in inbox, intent chat, o automaticamente per risk ≤ 2.

**Input:** `workflow_id`, `pre_filled_args`, `user_id`
**Output:** aggiornamento `AgentInboxItem` + notifica in-app

**Nodi in sequenza:**

```
load_workflow_template → validate_args → execute_steps → report_result
```

```python
# app/agent/graphs/workflow_graph.py

# Nodo: load_workflow_template
# Carica WorkflowTemplate dal WorkflowTemplateRegistry tramite workflow_id.
# Errore immediato se workflow_id non trovato.

# Nodo: validate_args
# Verifica che gli argomenti pre-compilati siano completi rispetto a required_args.
# Se mancano dati: chiede all'utente SOLO quelli mancanti (non re-chiede tutto).

# Nodo: execute_steps
# Esegue gli step del workflow in sequenza.
# Per ogni step: RiskEngine.compute_risk() → risk ≤ 2: auto | risk 3-4: Review Card | risk 5: refuse.
# Stesso meccanismo HITL della sezione 6.3.

# Nodo: report_result
# Aggiorna AgentInboxItem di origine come "acted".
# Invia notifica in-app all'utente con riepilogo eseguito/pendente/saltato.
```

### DailyDigestService

**Responsabilità:** genera il briefing giornaliero per ogni utente. Avviato da APScheduler alle 08:00. Non usa LangGraph — usa direttamente il service layer.

**Dipendenze:** `DeadlineRepository`, `InboxRepository`, `LLMProviderPort`, `NotifierPort`.

```python
# app/services/daily_digest_service.py

class DailyDigestService:
    async def generate_for_user(self, user_id: str) -> AgentInboxItem:
        """
        1. collect_situation: query DB senza LLM (deadline overdue, urgenti, questa settimana,
           documenti in pending_review, bozze in attesa, inbox items non risolti da >48h).
        2. detect_patterns: LLM leggero max 200 token (Phase 2: template strutturato; Phase 3: LLM).
        3. compose_digest: template Jinja2 + suggestion.
        4. write_inbox_item: event_type=daily_digest, urgency=immediate, expires_at=mezzanotte.
        """
        ...

    async def generate_for_all_users(self) -> None:
        """
        Chiamato dallo scheduler. Processa utenti in sequenza con rate limiting.
        Errore su un utente non blocca gli altri.
        """
        ...
```

### WorkflowTemplateRegistry

**Responsabilità:** registro centralizzato di tutti i `WorkflowTemplate` disponibili. Aggiungere un workflow = aggiungere un file in `app/agent/workflows/templates/` senza modifiche al core.

```python
# app/agent/workflows/registry.py

class WorkflowTemplateRegistry:
    def get(self, workflow_id: str) -> WorkflowTemplate:
        """Restituisce il template. Solleva KeyError se workflow_id non trovato."""
        ...

    def register(self, template: WorkflowTemplate) -> None:
        """Registra un nuovo template. Usato all'avvio per caricare i file da templates/."""
        ...

    def list_all(self) -> list[WorkflowTemplate]:
        """Restituisce tutti i template registrati."""
        ...
```

**Template MVP (Phase 2):** `draft_payment_reminder`, `process_document`, `create_deadline_from_document`.
**Template Phase 3:** `reply_to_email`, `generate_payment_status_report`, `batch_send_reminders`.

### DocumentService

**Responsabilità:** gestisce il ciclo di vita dei documenti: upload, recupero, ricerca semantica, archiviazione.

**Dipendenze:** `FileStoragePort`, `VectorStorePort`, `DocumentParserPort`, `AuditService`.

```python
# app/core/services/document_service.py

class DocumentService:
    async def upload(
        self, file: BinaryIO, filename: str, user_id: str, content_type: str
    ) -> Document:
        """
        Salva file su storage, crea record documents con parse_status=pending.
        Se storage fallisce: HTTP 503, nessun record DB creato.
        Avvia DocumentPipeline in background.
        """
        ...

    async def get(self, document_id: str, user_id: str) -> Document:
        """Restituisce documento. HTTP 403 se user_id non corrisponde."""
        ...

    async def search(
        self, query: str, user_id: str, filters: dict
    ) -> list[VectorSearchResult]:
        """Ricerca semantica su document_chunks filtrata per user_id. Max 10 risultati default."""
        ...
```

### DeadlineService

**Responsabilità:** gestisce scadenze: creazione manuale e da AI, notifiche preventive, ricorrenza.

**Dipendenze:** `NotifierPort`, `AuditService`.

```python
# app/core/services/deadline_service.py

class DeadlineService:
    async def create(self, deadline_data: dict, user_id: str) -> Deadline:
        """Crea scadenza con source=manual o source=ai_extracted."""
        ...

    async def get_upcoming(self, user_id: str, n: int = 10) -> list[Deadline]:
        """Restituisce le prossime N scadenze per il widget dashboard."""
        ...

    async def check_and_notify(self) -> None:
        """
        Chiamato dallo scheduler alle 08:00.
        Invia notifiche preventive per scadenze in notify_days_before.
        Applica soglie red_days/yellow_days per determinare il canale.
        """
        ...
```

### EmailDraftService

**Responsabilità:** gestisce il ciclo di vita delle bozze email con doppia conferma (contenuto + invio).

**Dipendenze:** `EmailSenderPort`, `AuditService`, `NotifierPort`.

```python
# app/core/services/email_draft_service.py

class EmailDraftService:
    async def create_draft(
        self, to: list[str], subject: str, body_html: str, body_text: str, user_id: str
    ) -> EmailDraft:
        """Crea bozza con status=pending_review."""
        ...

    async def approve(self, draft_id: str, user_id: str) -> PendingConfirmation:
        """
        Aggiorna bozza a status=approved.
        Crea PendingConfirmation con risk_level=4 per l'invio effettivo.
        """
        ...

    async def send(self, draft_id: str, user_id: str) -> bool:
        """
        Invia bozza approvata via EmailSenderPort.
        HTTP 422 se status != approved.
        Registra nell'AuditLog.
        """
        ...
```

### NotificationService

**Responsabilità:** dispatcha notifiche in-app e via email in base al livello e alle preferenze utente.

**Dipendenze:** `NotifierPort`.

```python
# app/core/services/notification_service.py

class NotificationService:
    async def dispatch(
        self,
        user_id: str,
        level: str,          # info | warning | urgent | action
        title: str,
        body: str,
        related_type: str | None,
        related_id: str | None,
    ) -> None:
        """
        Seleziona canali (inapp, email) in base a level + notification_settings utente.
        Crea record in notifications. Dispatcha via NotifierPort.
        """
        ...
```

### AuditService

**Responsabilità:** registra ogni azione del sistema nell'audit log append-only.

**Dipendenze:** nessuna porta esterna — scrive direttamente su DB.

```python
# app/core/services/audit_service.py

class AuditService:
    async def log(
        self,
        user_id: str,
        action_type: str,
        tool_name: str | None,
        input_summary: str,
        output_summary: str,
        risk_score: int | None,
        status: str,
        llm_model: str | None,
        session_id: str | None = None,
    ) -> None:
        """
        Inserisce record in audit_log. Mai UPDATE o DELETE su questa tabella.
        Non logga valori di segreti — solo riassunti.
        """
        ...
```

### FallbackChain

**Responsabilità:** orchestra i provider LLM in sequenza. Tenta PRIMARY → FALLBACK_1 → FALLBACK_2. Logga ogni fallback con motivo.

**Dipendenze:** implementazioni concrete di `LLMProviderPort` (Anthropic, OpenAI, Gemini).

```python
# app/adapters/llm/fallback_chain.py

class FallbackChain:
    async def generate(
        self, prompt: str, system: str, context: list[dict] | None = None
    ) -> LLMResponse:
        """
        Tenta i provider in ordine. Trigger: 5xx, timeout (45s), 429, connection refused.
        Se tutti falliscono: solleva eccezione con messaggio chiaro.
        """
        ...

    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]:
        """Streaming con fallback automatico al primo errore."""
        ...
```

### ParserWithFallback

**Responsabilità:** tenta il parser primario, cade sul fallback se `confidence < 0.60`. Restituisce il risultato con confidence più alta.

```python
# app/adapters/parsers/parser_with_fallback.py

class ParserWithFallback:
    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        """
        Tenta primary.parse(). Se confidence < 0.60 e fallback disponibile:
        tenta fallback.parse(). Restituisce max(primary, fallback, key=confidence).
        """
        ...
```

**Mapping parser per tipo file:**

| Content-Type | Parser primario | Parser fallback |
|---|---|---|
| `application/pdf` | LlamaParse | Unstructured.io |
| `application/vnd.ms-excel` | Unstructured.io | pandas |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Unstructured.io | pandas |
| `text/csv` | pandas | — |

### API Endpoints

Tutte le route sotto `/api/v1/`. Auth via JWT header `Authorization: Bearer <token>`.

```
AUTH
  POST   /auth/login                  Login con email/password → JWT

DOCUMENTS
  POST   /documents/upload            Carica documento, avvia pipeline asincrona
  GET    /documents                   Lista documenti (paginata, filtrata per type/status/date)
  GET    /documents/{id}              Dettaglio + metadati estratti
  GET    /documents/{id}/download     Download file originale
  DELETE /documents/{id}              Soft delete → crea PendingConfirmation risk_level=4 → HTTP 202
  POST   /documents/search            Ricerca semantica { query, filters }

DEADLINES
  GET    /deadlines                   Lista con filtri (status, type, date range)
  POST   /deadlines                   Crea manualmente
  PUT    /deadlines/{id}              Modifica
  DELETE /deadlines/{id}              Cancella → crea PendingConfirmation risk_level=3
  GET    /deadlines/upcoming          Prossime N scadenze per dashboard

AGENT INBOX
  GET    /inbox                       Lista items (filtro: status, urgency) ordinati per urgency
  GET    /inbox/unread-count          Count per badge header
  POST   /inbox/{id}/act              Esegui azione suggerita { action_id }
  POST   /inbox/{id}/dismiss          Segna come gestito manualmente
  POST   /inbox/trigger-triage        Forza triage manuale su un evento (dev/debug)

AGENT
  POST   /agent/query                 Chat con l'agente { message, session_id }
  GET    /agent/sessions/{id}         Stato sessione (azioni eseguite, pending, saltate)
  GET    /agent/tasks                 Task utente (filtri per status)

HITL
  GET    /confirmations               Lista conferme pendenti
  POST   /confirmations/{id}/approve  Approva con dati facoltativamente modificati
  POST   /confirmations/{id}/reject   Rifiuta con commento opzionale

EMAIL DRAFTS
  GET    /email-drafts                Lista bozze (filtro per status)
  GET    /email-drafts/{id}           Dettaglio bozza con preview HTML
  PUT    /email-drafts/{id}           Modifica bozza (solo se status=pending_review)
  POST   /email-drafts/{id}/approve   Approva → crea PendingConfirmation risk_level=4
  POST   /email-drafts/{id}/send      Invia bozza approvata (HTTP 422 se non approved)
  DELETE /email-drafts/{id}           Cancella bozza

NOTIFICATIONS
  GET    /notifications               Lista notifiche (unread first, paginata)
  POST   /notifications/{id}/read     Marca come letta
  POST   /notifications/read-all      Marca tutte come lette

DASHBOARD
  GET    /dashboard/overview          Semaforo scadenze, contatori, attività recente

AUDIT
  GET    /audit-log                   Log azioni (paginato, filtrato per tipo/data)

SETTINGS
  GET    /settings                    Preferenze utente (soglie, canali notifiche)
  PUT    /settings                    Aggiorna preferenze

HEALTH
  GET    /health                      { status: "ok" | "degraded", checks: {...} }
```

---

## Data Models

### Domain Models (Pydantic v2)

```python
# app/core/domain/document.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class Document(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    original_filename: str
    storage_key: str
    content_type: str
    size_bytes: int | None
    document_type: str | None          # fattura | contratto | nota_spese | altro
    document_type_confidence: float | None
    extracted_metadata: dict           # JSONB con campi estratti + confidence per campo
    tags: list[str]
    parse_status: str                  # pending | parsed | failed
    created_at: datetime
    archived_at: datetime | None
```

```python
# app/core/domain/deadline.py
from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID

class Deadline(BaseModel):
    id: UUID
    user_id: UUID
    document_id: UUID | None
    title: str
    description: str | None
    due_date: date
    deadline_type: str                 # PAYMENT | CONTRACT_RENEWAL | TAX | LEGAL | CUSTOM
    recurrence: str                    # none | monthly | quarterly | semi_annual | annual | custom
    recurrence_config: dict            # cron expression se recurrence=custom
    status: str                        # active | completed | cancelled
    source: str                        # manual | ai_extracted | confirmed
    source_confidence: float | None
    source_text: str | None            # estratto testuale usato per estrazione
    notified_at: list[dict]            # [{ days_before, notified_at }]
    created_at: datetime
```

```python
# app/core/domain/task.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class AgentTask(BaseModel):
    id: UUID
    user_id: UUID
    session_id: str | None
    action_type: str
    tool_name: str | None
    tool_args: dict
    status: str  # pending | in_progress | waiting_confirmation | approved | done | failed | skipped | rejected
    risk_score: int
    depends_on_task_id: UUID | None
    result: dict | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
```

```python
# app/core/domain/pending_confirmation.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class PendingConfirmation(BaseModel):
    id: UUID
    task_id: UUID
    user_id: UUID
    description: str               # Human-readable: "Vuoi creare scadenza X?"
    data_for_review: dict          # Dati pre-compilati per revisione
    risk_level: str
    status: str                    # pending | approved | rejected
    user_comment: str | None
    group_id: UUID | None          # stesso group_id = stessa Review Card
    group_type: str | None         # document_review | standalone
    created_at: datetime
    resolved_at: datetime | None
```

```python
# app/core/domain/email_draft.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class EmailDraft(BaseModel):
    id: UUID
    user_id: UUID
    task_id: UUID | None
    to_addresses: list[str]
    subject: str
    body_html: str
    body_text: str
    status: str                    # pending_review | approved | sent | rejected
    approved_at: datetime | None
    sent_at: datetime | None
    created_at: datetime
```

```python
# app/core/domain/notification.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class Notification(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str | None
    level: str                     # info | warning | urgent | action
    related_type: str | None       # deadline | document | confirmation | email_draft
    related_id: UUID | None
    read: bool
    created_at: datetime
```

```python
# app/core/domain/audit_entry.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class AuditEntry(BaseModel):
    id: UUID
    user_id: UUID | None
    session_id: str | None
    action_type: str
    tool_name: str | None
    input_summary: str | None      # Riassunto, non dati sensibili grezzi
    output_summary: str | None
    risk_score: int | None
    status: str | None
    llm_model: str | None
    created_at: datetime
```

```python
# app/core/domain/inbox.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class AgentInboxItem(BaseModel):
    id: UUID
    user_id: UUID
    event_type: str                # document_uploaded | email_received | deadline_approaching |
                                   # deadline_overdue | user_chat_message | manual_trigger | daily_digest
    event_source: dict             # { type, from, subject, document_id, ... }
    source_ref_id: UUID | None     # document_id / deadline_id / email_id se applicabile
    agent_analysis: str            # testo human-readable: cosa l'agente ha capito
    urgency: str                   # immediate | today | this_week | low
    suggested_actions: list[dict]  # [{ id, label, workflow_id, pre_filled_args, risk_score, estimated_seconds }]
    status: str                    # pending | acted | dismissed | expired
    chosen_action_id: str | None
    chosen_at: datetime | None
    created_at: datetime
    expires_at: datetime | None    # None = non scade. Daily digest scade a mezzanotte.

class AgentEvent(BaseModel):
    event_id: str
    event_type: str                # AgentEventType enum
    user_id: str
    payload: dict
    received_at: datetime
    source_ref: str | None         # es. document_id, email_id, deadline_id
```

```python
# app/agent/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    user_id: str
    session_id: str
    triggering_event: AgentEvent | None     # se avviato da evento
    messages: Annotated[list, add_messages] # se avviato da chat
    active_workflow_id: str | None
    workflow_args: dict
    planned_steps: list[dict]               # list[PlannedAction]
    current_step_index: int
    executed_steps: list[dict]              # list[ExecutedAction]
    pending_confirmations: list[dict]       # list[PendingConfirmation]
    inbox_item_id: str | None
    final_response: str
    errors: list[str]
```

```python
# app/agent/workflows/registry.py
from pydantic import BaseModel

class WorkflowStep(BaseModel):
    tool: str
    risk: int
    args_mapping: dict             # mapping da workflow_args ai parametri del tool

class WorkflowTemplate(BaseModel):
    workflow_id: str
    name: str                      # "Invia sollecito pagamento"
    description: str               # usato dall'intent_classifier
    required_args: list[str]
    optional_args: list[str]
    steps: list[WorkflowStep]
    applicable_to: list[str]       # event_types a cui si applica naturalmente
```

```python
# app/core/domain/trust.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class UserExtractionTrust(BaseModel):
    user_id: UUID
    document_type: str
    field_name: str
    total_extractions: int
    confirmed_without_edit: int    # utente ha confermato senza modificare
    edited_extractions: int        # utente ha corretto il valore
    accuracy: float | None         # colonna generata: confirmed_without_edit / total_extractions
    last_updated: datetime
```

### Schema SQL Completo

```sql
-- [TODO: multi-tenancy] su ogni tabella

-- Utenti
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'owner',    -- owner | admin | viewer [DEFERRED: RBAC TD-006]
    notification_settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
    -- [TODO: multi-tenancy] ADD COLUMN tenant_id UUID
);

-- Documenti
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    storage_key VARCHAR(1000) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER,
    document_type VARCHAR(100),
    document_type_confidence FLOAT,
    extracted_metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    parse_status VARCHAR(50) DEFAULT 'pending',  -- pending | parsed | failed
    created_at TIMESTAMPTZ DEFAULT now(),
    archived_at TIMESTAMPTZ
    -- [TODO: multi-tenancy]
);

-- Chunk vettoriali (pgvector)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
    -- [TODO: multi-tenancy]
);

CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX ON document_chunks (user_id);

-- Scadenze
CREATE TABLE deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    deadline_type VARCHAR(100) DEFAULT 'custom',
    recurrence VARCHAR(50) DEFAULT 'none',
    recurrence_config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',  -- active | completed | cancelled
    source VARCHAR(50) DEFAULT 'manual',  -- manual | ai_extracted | confirmed
    source_confidence FLOAT,
    source_text TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    notified_at JSONB DEFAULT '[]'
    -- [TODO: multi-tenancy]
);

-- Task Agent
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id VARCHAR(255),
    action_type VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100),
    tool_args JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    risk_score INTEGER NOT NULL,
    depends_on_task_id UUID REFERENCES agent_tasks(id),
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
    -- [TODO: multi-tenancy]
);

-- Conferme HITL
CREATE TABLE pending_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES agent_tasks(id),
    user_id UUID NOT NULL REFERENCES users(id),
    description TEXT NOT NULL,
    data_for_review JSONB NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending | approved | rejected
    user_comment TEXT,
    group_id UUID,                          -- stesso group_id = stessa Review Card
    group_type VARCHAR(100),                -- document_review | standalone
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
    -- [TODO: multi-tenancy]
);

CREATE INDEX ON pending_confirmations (group_id) WHERE group_id IS NOT NULL;

-- Bozze Email
CREATE TABLE email_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    task_id UUID REFERENCES agent_tasks(id),
    to_addresses TEXT[] NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending_review',
    approved_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
    -- [TODO: multi-tenancy]
);

-- Notifiche In-App
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    body TEXT,
    level VARCHAR(50) NOT NULL,          -- info | warning | urgent | action
    related_type VARCHAR(100),
    related_id UUID,
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
    -- [TODO: multi-tenancy]
);

-- Audit Log (append-only — nessun UPDATE o DELETE tramite API)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    action_type VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100),
    input_summary TEXT,
    output_summary TEXT,
    risk_score INTEGER,
    status VARCHAR(50),
    llm_model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now()
    -- [TODO: multi-tenancy]
);

-- Agent Inbox
CREATE TABLE agent_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    event_type VARCHAR(100) NOT NULL,
    event_source JSONB NOT NULL,
    source_ref_id UUID,
    agent_analysis TEXT NOT NULL,
    urgency VARCHAR(50) NOT NULL,          -- immediate | today | this_week | low
    suggested_actions JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending | acted | dismissed | expired
    chosen_action_id VARCHAR(100),
    chosen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ
    -- [TODO: multi-tenancy]
);

CREATE INDEX ON agent_inbox (user_id, status, urgency, created_at DESC);

-- Trust Progressivo (schema Phase 0, logica Phase 3)
CREATE TABLE user_extraction_trust (
    user_id UUID NOT NULL REFERENCES users(id),
    document_type VARCHAR(100) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    total_extractions INTEGER DEFAULT 0,
    confirmed_without_edit INTEGER DEFAULT 0,
    edited_extractions INTEGER DEFAULT 0,
    accuracy FLOAT GENERATED ALWAYS AS (
        confirmed_without_edit::float / NULLIF(total_extractions, 0)
    ) STORED,
    last_updated TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, document_type, field_name)
    -- [TODO: multi-tenancy]
);
```

---

## Correctness Properties

*Una proprietà è una caratteristica o comportamento che deve essere vera per tutte le esecuzioni
valide di un sistema — essenzialmente, un'affermazione formale su cosa il sistema deve fare.
Le proprietà fungono da ponte tra specifiche leggibili dall'uomo e garanzie di correttezza
verificabili automaticamente.*

Le proprietà seguenti sono state derivate dall'analisi delle acceptance criteria dei requisiti.
Ogni proprietà è universalmente quantificata e implementabile come test property-based
con la libreria **Hypothesis** (Python).

### Property 1: Risk Score Monotonicity

*Per qualsiasi* azione pianificata con un tool_name valido e qualsiasi sottoinsieme di
modificatori di contesto, il valore restituito da `compute_risk(action, context)` deve
essere sempre compreso nell'intervallo `[risk_base, 5]`. In particolare, aggiungere
modificatori di contesto non può mai abbassare il risk score rispetto al valore base
del tool, e il risk score non può mai superare 5.

**Validates: Requirements 7.2, 7.7**

### Property 2: Confidence Gate Completeness

*Per qualsiasi* documento con campi estratti e confidence score associati, dopo
l'esecuzione del nodo `confidence_gate`, il numero di `PendingConfirmation` create
deve essere esattamente uguale al numero di campi la cui confidence è inferiore alla
soglia configurata per quel tipo di campo in `rules.yaml`. Nessun campo sotto-soglia
può essere salvato in `extracted_metadata` senza una `PendingConfirmation` corrispondente.

**Validates: Requirements 5.9, 6.1, 6.2**

### Property 3: HITL Invariant

*Per qualsiasi* azione pianificata con `risk_score >= 3`, il sistema non deve mai
eseguire il tool associato senza che esista una `PendingConfirmation` con `status=approved`
per quella specifica azione. Questa proprietà deve valere indipendentemente dall'ordine
di arrivo delle approvazioni e dalla presenza di altre azioni nella coda.

**Validates: Requirements 7.4, 7.5, 8.1, 8.9**

### Property 4: Audit Log Append-Only

*Per qualsiasi* sequenza di operazioni eseguite sul sistema (incluse operazioni di
creazione, modifica, eliminazione su qualsiasi altra tabella), il conteggio totale
dei record nella tabella `audit_log` deve essere monotonicamente non-decrescente.
Nessuna operazione può ridurre il numero di record nell'audit log.

**Validates: Requirements 19.2**

### Property 5: Parser Round-Trip

*Per qualsiasi* `ParsedDocument` valido (con campi `text`, `tables`, `metadata`,
`raw_pages`, `confidence` non nulli), serializzare il documento in JSON e poi
deserializzarlo deve produrre un oggetto con campi chiave identici all'originale.
I campi chiave sono: `text`, `tables`, `metadata`, `confidence`.

**Validates: Requirements 25.5**

### Property 6: Inbox Urgency Ordering

*Per qualsiasi* insieme di `AgentInboxItem` con urgency mista presenti nel database
per un utente, la risposta di `GET /inbox` deve restituire gli item in ordine tale
che per ogni coppia di item adiacenti `(i, j)` con `i` prima di `j` nell'output,
`urgency_rank(i) <= urgency_rank(j)`, dove il ranking è:
`immediate=0 < today=1 < this_week=2 < low=3`.
A parità di urgency, gli item più recenti (`created_at DESC`) vengono prima.

**Validates: Requirements 10.1**

### Property 7: Workflow Template Completeness

*Per qualsiasi* `AgentInboxItem` prodotto dal `TriageGraph` o dal `DailyDigestGraph`,
ogni `workflow_id` presente nel campo `suggested_actions` deve corrispondere a un
template registrato nel `WorkflowTemplateRegistry`. Non deve mai esistere un
`AgentInboxItem` con un `workflow_id` che non sia risolvibile dal registry al momento
dell'esecuzione.

**Validates: Requirements 11.6, 11.7**

---

## Error Handling

### Principi Generali

- **Fail loudly on risk, silently on safe**: azioni sicure → log + esegui; azioni rischiose → sospendi + notifica.
- Nessuna eccezione non tipizzata. Definire `ACGException` base con sottoclassi specifiche.
- Ogni service ha un `logger = structlog.get_logger(__name__)` con formato JSON strutturato.
- Mai loggare valori di segreti (API key, password, token JWT).

### Gestione Errori per Componente

**DocumentPipeline:**
- Parser fallisce su tutti i parser disponibili → `parse_status=failed`, notifica `level=warning`, log audit
- LLM fallisce durante classificazione/estrazione → `parse_status=failed`, notifica `level=warning`, log audit
- `VectorStorePort.upsert` fallisce → log audit, `parse_status=failed`
- Upload su storage fallisce → HTTP 503, nessun record DB creato

**TriageGraph:**
- LLM fallisce durante `classify_urgency` (this_week/low) → fallback deterministico: `this_week`
- Scrittura su `agent_inbox` fallisce → log audit, termina senza notifica

**WorkflowGraph:**
- `workflow_id` non trovato nel registry → errore immediato, notifica utente
- Tool fallisce dopo approvazione (risk ≥ 4) → `status=failed`, log audit, notifica `level=warning`
- Nessun retry automatico su azioni risk ≥ 4

**LLM FallbackChain:**
- Provider primario fallisce → tenta FALLBACK_1, poi FALLBACK_2
- Tutti i provider falliscono → errore all'utente con messaggio chiaro, log ogni fallback con motivo

**RiskEngine:**
- `rules.yaml` assente o malformato all'avvio → exit code non-zero, log dettaglio errore

**Auth:**
- JWT scaduto/non valido → HTTP 401 con motivo (`token_expired`, `token_invalid`)
- Credenziali non valide → HTTP 401 con messaggio generico (no user enumeration)
- Accesso a risorsa di altro utente → HTTP 403

**Guardrail violations:**
- Output viola Constitution → blocca output, sostituisce con messaggio standard, log audit con `action_type=guardrail_block`
- Richiesta in Blacklist → rifiuto immediato con spiegazione, log audit

### Codici HTTP Standard

| Codice | Quando |
|---|---|
| 202 | Azione accettata ma non ancora eseguita (es. DELETE → PendingConfirmation creata) |
| 401 | JWT assente, scaduto o non valido |
| 403 | Risorsa di un altro utente |
| 404 | Risorsa non trovata |
| 415 | Content-Type non supportato |
| 422 | Input malformato o stato non valido (es. send su bozza non approved) |
| 503 | Storage backend non disponibile |

---

## Testing Strategy

### Dual Testing Approach

Il progetto usa sia **unit test** (pytest) che **property-based test** (Hypothesis) per una copertura complementare:

- **Unit test**: comportamenti specifici, edge case, integrazione tra componenti.
- **Property test**: proprietà universali che devono valere per tutti gli input validi.

### Property-Based Testing (Hypothesis)

La libreria scelta è **[Hypothesis](https://hypothesis.readthedocs.io/)** per Python. Ogni property test deve girare con un minimo di 100 iterazioni (default Hypothesis).

Ogni test è annotato con un tag che referenzia la proprietà del design:

```python
# Tag format: Feature: acg-mvp, Property {N}: {property_text}
@given(st.text(min_size=1).filter(lambda s: s.strip()))
@settings(max_examples=100)
def test_storage_key_format(filename: str) -> None:
    """Feature: acg-mvp, Property 5: Storage key segue il formato corretto"""
    user_id = str(uuid4())
    file_id = str(uuid4())
    key = build_storage_key(user_id, file_id, filename)
    assert key.startswith(f"{user_id}/")
    assert key.endswith(f"_{filename}")
    parts = key.split("/")
    assert len(parts) == 4  # user_id/year/month/file_id_filename
```

### Test Structure

```
tests/
├── unit/
│   ├── test_risk_engine.py          # Properties 1 (Risk Score Monotonicity)
│   ├── test_guardrail_layer.py      # Properties 3 (HITL Invariant), blacklist
│   ├── test_triage_graph.py         # TriageGraph urgency rules, max 3 actions
│   ├── test_inbox_ordering.py       # Property 6 (Inbox Urgency Ordering)
│   ├── test_storage_key.py          # Storage key format
│   ├── test_chunking.py             # Chunk size/overlap invariants
│   ├── test_confidence_gate.py      # Property 2 (Confidence Gate Completeness)
│   ├── test_task_state_machine.py   # HITL state machine transitions
│   ├── test_fallback_chain.py       # FallbackChain trigger logic
│   ├── test_audit_log.py            # Property 4 (Audit Log Append-Only)
│   ├── test_parsed_document.py      # Property 5 (Parser Round-Trip)
│   ├── test_auth.py                 # JWT validation, user isolation
│   ├── test_protocols.py            # Dummy implementations per ogni Protocol
│   └── test_services/
│       ├── test_document_service.py
│       ├── test_deadline_service.py
│       ├── test_email_draft_service.py
│       ├── test_notification_service.py
│       └── test_audit_service.py
└── integration/
    ├── test_document_pipeline.py    # Pipeline completa con file reali
    ├── test_api_endpoints.py        # HTTP 401/403/422 per ogni endpoint
    ├── test_workflow_templates.py   # Esecuzione completa di ogni template
    └── test_parsers.py              # Parser con file di esempio reali
```

### Unit Test Requirements

- Ogni service del core ha test con mock che implementano i Protocol.
- `RiskEngine`: test per ogni livello (0-5) con e senza modificatori di contesto.
- `GuardrailLayer`: test per blocco blacklist e violazioni Constitution.
- Ogni Protocol ha almeno un test che verifica l'interfaccia con il dummy.
- Ogni WorkflowTemplate ha almeno un test di esecuzione completa con adapter mock.

### Integration Test Requirements

- `DocumentPipeline`: test con file reali (PDF strutturato, PDF scansionato, XLSX, CSV).
- Ogni endpoint REST: risposta corretta per input valido, HTTP 401 non autenticato, HTTP 422 input malformato.
- Parser: almeno un documento di esempio per tipo supportato.

### Property Test Mapping

| Property | Test File | Hypothesis Strategy |
|---|---|---|
| 1 — Risk Score Monotonicity | `test_risk_engine.py` | `st.integers(0, 5)` + modifiers |
| 2 — Confidence Gate Completeness | `test_confidence_gate.py` | `st.lists(st.floats(0.0, 1.0))` |
| 3 — HITL Invariant | `test_task_state_machine.py` | `st.integers(3, 5)` per risk |
| 4 — Audit Log Append-Only | `test_audit_log.py` | `st.builds(AuditEntry)` |
| 5 — Parser Round-Trip | `test_parsed_document.py` | `st.builds(ParsedDocument)` |
| 6 — Inbox Urgency Ordering | `test_inbox_ordering.py` | `st.lists(st.builds(AgentInboxItem))` |
| 7 — Workflow Template Completeness | `test_triage_graph.py` | `st.builds(AgentEvent)` |

### Code Quality

- `mypy --strict` deve passare su tutto il backend.
- Nessun `print()` nel codice: solo `structlog`.
- Nessun `import` di adapter in `app/core/`.
- Nessun global state nell'agent.
- Nessun prompt hardcodato nel codice Python.

### Development Phases

#### Phase 0 — Foundation (Settimana 1)

- [ ] Tutti i Protocol/Port definiti con implementazioni dummy funzionanti
- [ ] Schema DB completo (tutte le tabelle incluse `agent_inbox`, `user_extraction_trust`)
- [ ] Docker Compose: PostgreSQL + MinIO + backend + frontend con health check
- [ ] Auth JWT locale (bcrypt cost factor ≥ 12) + endpoint `/auth/login`
- [ ] `WorkflowTemplateRegistry` stub (struttura pronta, 0 template)
- [ ] `rules.yaml` con valori di default
- [ ] Migration Alembic iniziale con tutti i commenti `[TODO: multi-tenancy]`
- [ ] `infra/env.example` con tutte le variabili documentate

**Deliverable:** `docker-compose up` → backend risponde su :8000, frontend su :3000.

#### Phase 1 — Document Core (Settimane 2-4)

- [ ] Upload documenti (PDF, XLSX, XLS, CSV) con validazione Content-Type
- [ ] DocumentPipelineGraph: parsing → classificazione → estrazione campi → confidence gate
- [ ] ParserWithFallback (LlamaParse + Unstructured per PDF; Unstructured + pandas per XLS)
- [ ] VectorStore: chunking + embedding + pgvector upsert
- [ ] Review Card aggregata (group_id) con frontend `ReviewCard` component
- [ ] TriageGraph per eventi `DOCUMENT_UPLOADED` (senza LLM avanzato)
- [ ] `AgentInboxItem` scritto su DB dopo ogni upload
- [ ] Frontend: `InboxCard` base, dashboard inbox-first layout, `DocumentUploadZone`

**Deliverable:** Upload PDF → Review Card aggregata in inbox → conferma → documento archiviato.

#### Phase 2 — Intelligence + Inbox (Settimane 5-7)

- [ ] TriageGraph completo per tutti gli event types
- [ ] WorkflowGraph con 3 template: `draft_payment_reminder`, `process_document`, `create_deadline_from_document`
- [ ] `DailyDigestService` + scheduler 08:00 (template strutturato, senza LLM avanzato)
- [ ] `InboxCard` completa con tutti gli stili urgency
- [ ] Chat agent con intent mapping → workflow template
- [ ] Deadline engine + notification system
- [ ] Email drafting con SMTP (two-step confirmation)
- [ ] Guardrails layer (tutti e 3 i livelli)
- [ ] `ConfirmationCard`, `EmailDraftPreview`, `DeadlineSemaphore`

**Deliverable:** Daily digest ogni mattina. Email ricevuta → triage → card in inbox → azione in 2 click.

#### Phase 3 — Polish & Production (Settimane 8-10)

- [ ] Trust progressivo: `RiskEngine.effective_threshold()` legge `user_extraction_trust`
- [ ] `detect_patterns()` nel digest con LLM (suggerimento del giorno)
- [ ] Workflow template aggiuntivi: `reply_to_email`, `generate_payment_status_report`, `batch_send_reminders`
- [ ] Digest email opzionale (versione HTML via SMTP)
- [ ] LangSmith tracing (`LANGSMITH_ENABLED=true`)
- [ ] Testing con dataset realistico
- [ ] Security review
- [ ] Docker Compose production-ready
- [ ] Google Calendar adapter (stretch goal)
- [ ] Documentazione API

### Technical Debt Register

| ID | Cosa | Dove | Note |
|---|---|---|---|
| `TD-001` | Multi-tenancy RLS | Tutte le tabelle DB + adapter | Aggiunge `tenant_id` a ogni query. Stub: filtro solo per `user_id` |
| `TD-002` | n8n integration | `adapters/automation/` non esiste | Porta `AutomationPort` da aggiungere |
| `TD-003` | ML Risk Scoring | `agent/risk/engine.py` | Sezione commentata in `rules.yaml`. Sostituisce rules-based con modello trained |
| `TD-004` | Feedback loop | `api/v1/feedback.py` non esiste | Tabella `llm_feedback` da aggiungere |
| `TD-005` | White-label theming | Frontend CSS variables | Design token system pronto, switching non implementato |
| `TD-006` | RBAC avanzato | `users.role` solo stringa | Roles: owner/admin/viewer/approver |
| `TD-007` | Billing/subscription | Non esiste | Usage metering necessario prima del lancio commercial |
| `TD-008` | File encryption at rest | Storage adapters | MinIO/S3 server-side encryption |
| `TD-009` | Mobile app | Non esiste | PWA come primo step |
| `TD-010` | Email receiving nativo | Non esiste | SMTP inbound (Postal/Mailgun) per catturare email senza forwarding manuale |
| `TD-011` | Workflow template via UI | `agent/workflows/templates/` | Editor no-code per workflow custom |
| `TD-012` | Digest personalizzazione | `services/daily_digest_service.py` | Formato e contenuto digest fisso nell'MVP |
| `TD-013` | Pattern detection avanzata | `detect_patterns()` | Modello trained su dati storici utente |
