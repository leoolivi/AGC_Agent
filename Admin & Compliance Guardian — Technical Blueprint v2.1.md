**Data:** 30 Maggio 2026  
**Stato:** Specifica definitiva MVP — documento unificato  
**Destinatario:** AI coding assistant (Claude Code / GPT-4o / Cursor)

**Changelog v2.1:**

- §5 Agent Design: rimpiazzato con modello Triage/Inbox (TriageGraph, WorkflowGraph, DailyDigestGraph)
- §6.4 Review Card aggregata per documento
- §6.5 Trust Progressivo — schema Phase 0, logica Phase 3
- §11bis Daily Digest & Proactive Scheduler
- §14bis Agent Inbox — schema DB, API, dashboard layout
- §17 Development Phases ribilanciate (inbox-first da Phase 1)
- §18 Technical Debt Register espanso (TD-010..013)

**Changelog v2.1:**

- Aggiunto sistema Action Feed & Triage come paradigma UX primario
- Review Card aggregata per documento (sostituisce PendingConfirmation multipli)
- ProactiveSchedulerGraph come feature di punta
- Workflow templates come quick-action secondari (non entry point primario)
- Trust progressivo spostato in Phase 3 con schema DB già in Phase 0
- Frontend ristrutturato attorno all'Action Feed

---

## 0. Scopo di questo documento

Questo documento è la **fonte di verità tecnica** per lo sviluppo del prodotto. Ogni decisione architetturale è definitiva salvo nota esplicita. I punti marcati `[DEFERRED]` sono debito tecnico consapevole — vanno implementati come stub/dummy nell'MVP senza creare blocchi. I punti marcati `[FORBIDDEN_MVP]` non vanno implementati né lasciati come stub: rifiutati a runtime.

Regola d'oro: **Reliability > Autonomy**. Il sistema fa più lavoro possibile da solo, ma delega sempre la responsabilità finale a un essere umano per ogni azione che può causare danni.

---

## 1. Principi Guida

|#|Principio|Implicazione pratica|
|---|---|---|
|1|**Human owns mistakes**|Ogni azione con effetti esterni richiede approvazione esplicita|
|2|**Fail loudly on risk, silently on safe**|Azioni sicure: log + esegui. Azioni rischiose: sospendi + notifica|
|3|**Confidence gate on AI extraction**|Ogni dato estratto da AI con confidence < soglia va in coda conferma|
|4|**Protocols as contracts**|Nessun modulo dipende da implementazioni concrete — solo da Protocol|
|5|**Linear task queue**|No grafi complessi di task paralleli nell'MVP. Queue lineare con skip dei bloccati|
|6|**Stub today, swap tomorrow**|Tutto ciò che è `[DEFERRED]` ha un'interfaccia reale ma implementazione dummy|

---

## 2. Overview del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                                │
│   [REST API]         [File Upload Webhook]      [Scheduler]         │
└──────────┬──────────────────┬──────────────────────┬───────────────┘
           │                  │                      │
           ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│   ChatAgentService   DocumentPipelineService   DeadlineService      │
│   EmailDraftService  NotificationService       AuditService         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   AGENT CORE     │ │  STORAGE PORTS   │ │  EXTERNAL PORTS  │
│   (LangGraph)    │ │  FileStorage     │ │  LLMProvider     │
│   ActionQueue    │ │  VectorStore     │ │  EmailSender     │
│   RiskEngine     │ │  Database (ORM)  │ │  CalendarPort    │
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

---

## 3. Architettura Esagonale — Struttura Directory

```
acg/
├── backend/
│   ├── app/
│   │   ├── core/                      # Business logic pura, zero dipendenze esterne
│   │   │   ├── domain/                # Entità e value objects
│   │   │   │   ├── document.py
│   │   │   │   ├── deadline.py
│   │   │   │   ├── task.py
│   │   │   │   ├── email_draft.py
│   │   │   │   └── audit_entry.py
│   │   │   ├── ports/                 # Protocol definitions (interfaces)
│   │   │   │   ├── storage.py         # FileStoragePort, VectorStorePort
│   │   │   │   ├── llm.py             # LLMProviderPort
│   │   │   │   ├── email.py           # EmailSenderPort
│   │   │   │   ├── calendar.py        # CalendarPort
│   │   │   │   ├── parser.py          # DocumentParserPort
│   │   │   │   └── notifier.py        # NotifierPort
│   │   │   └── services/              # Use cases
│   │   │       ├── document_service.py
│   │   │       ├── deadline_service.py
│   │   │       ├── email_draft_service.py
│   │   │       ├── notification_service.py
│   │   │       └── audit_service.py
│   │   ├── agent/                     # LangGraph agent
│   │   │   ├── graphs/
│   │   │   │   ├── document_pipeline.py
│   │   │   │   └── chat_agent.py
│   │   │   ├── nodes/                 # Singoli nodi LangGraph
│   │   │   │   ├── classifier.py
│   │   │   │   ├── planner.py
│   │   │   │   ├── risk_assessor.py
│   │   │   │   ├── executor.py
│   │   │   │   └── hitl_gate.py
│   │   │   ├── tools/                 # Tool registry
│   │   │   │   ├── search_tool.py
│   │   │   │   ├── deadline_tool.py
│   │   │   │   ├── draft_tool.py
│   │   │   │   └── document_tool.py
│   │   │   ├── risk/
│   │   │   │   ├── rules.yaml         # Risk rules (modifiable without redeploy)
│   │   │   │   ├── engine.py          # RiskEngine (legge rules.yaml)
│   │   │   │   └── classifier.py      # ActionClassifier
│   │   │   └── guardrails/
│   │   │       ├── constitution.md    # Costituzione dell'agente (hard-coded by default)
│   │   │       ├── blacklist.yaml     # Azioni vietate MVP
│   │   │       └── guardrail_layer.py
│   │   ├── adapters/                  # Implementazioni concrete dei Port
│   │   │   ├── storage/
│   │   │   │   ├── local_storage.py   # Dev dummy
│   │   │   │   ├── minio_storage.py   # Self-hosted
│   │   │   │   └── s3_storage.py      # Cloud
│   │   │   ├── llm/
│   │   │   │   ├── anthropic_adapter.py
│   │   │   │   ├── openai_adapter.py  # GPT-4o fallback
│   │   │   │   ├── gemini_adapter.py  # Gemini fallback
│   │   │   │   └── fallback_chain.py  # Orchestrazione fallback
│   │   │   ├── parsers/
│   │   │   │   ├── pdf_parser.py      # LlamaParse + Unstructured fallback
│   │   │   │   └── spreadsheet_parser.py  # Unstructured / pandas
│   │   │   ├── email/
│   │   │   │   └── smtp_adapter.py
│   │   │   ├── calendar/
│   │   │   │   └── google_calendar_adapter.py  # [DEFERRED: stub in MVP]
│   │   │   ├── vector/
│   │   │   │   └── pgvector_adapter.py
│   │   │   └── notifier/
│   │   │       ├── inapp_notifier.py
│   │   │       └── email_notifier.py
│   │   ├── api/                       # FastAPI routers
│   │   │   ├── v1/
│   │   │   │   ├── documents.py
│   │   │   │   ├── deadlines.py
│   │   │   │   ├── tasks.py           # HITL queue endpoints
│   │   │   │   ├── email_drafts.py
│   │   │   │   ├── agent.py           # Chat endpoint
│   │   │   │   ├── audit.py
│   │   │   │   └── dashboard.py
│   │   │   └── deps.py                # Dependency injection
│   │   ├── db/
│   │   │   ├── models.py              # SQLAlchemy models
│   │   │   └── migrations/            # Alembic
│   │   ├── config.py                  # Settings da env vars
│   │   └── main.py                    # FastAPI app factory
│   ├── tests/
│   │   ├── unit/                      # Test core/ con mock dei port
│   │   └── integration/               # Test con adapters reali
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/                       # Typed API client (openapi-ts o axios)
│   │   └── store/                     # Zustand o React Query
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml                 # Self-hosted: postgres, minio, backend, frontend
├── docker-compose.cloud.yml           # Cloud: punta a Supabase/Neon, S3
└── infra/
    └── env.example                    # Tutte le variabili con documentazione inline
```

---

## 4. Core Protocols (Python Protocol definitions)

Ogni port è un `typing.Protocol`. Nessun `import` di adapter nel core.

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

# app/core/ports/llm.py
@dataclass
class LLMResponse:
    content: str
    model: str
    confidence: float | None  # None se il modello non lo espone
    raw: dict                  # Response grezza per debug

class LLMProviderPort(Protocol):
    async def generate(self, prompt: str, system: str, context: list[dict] | None = None) -> LLMResponse: ...
    async def stream(self, prompt: str, system: str) -> AsyncIterator[str]: ...

# app/core/ports/parser.py
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

# app/core/ports/email.py
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

# app/core/ports/vector.py
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

# app/core/ports/calendar.py
@dataclass
class CalendarEvent:
    title: str
    due_datetime: datetime
    description: str
    external_id: str | None = None

class CalendarPort(Protocol):
    async def create_event(self, event: CalendarEvent, user_id: str) -> str: ...  # returns event_id
    async def delete_event(self, event_id: str, user_id: str) -> bool: ...

# app/core/ports/notifier.py
class NotifierPort(Protocol):
    async def send_inapp(self, user_id: str, title: str, body: str, level: str) -> bool: ...
    async def send_email_notification(self, user_id: str, subject: str, body: str) -> bool: ...
```

> **Nota implementazione:** Ogni adapter implementa il Protocol corrispondente. Il wiring avviene in `app/api/deps.py` tramite variabili d'ambiente. I test unitari del core usano sempre mock che implementano il Protocol.

---

## 5. Agent Design — LangGraph

### 5.1 Modello Mentale: l'Agente Come Assistente Umano

L'agente non è un chatbot che risponde a domande. È un **assistente che monitora, ragiona e propone**. Il flusso corretto da tenere a mente durante l'implementazione:

```
Un assistente umano valido non aspetta che tu gli chieda qualcosa.
Quando arriva una mail, la legge, capisce cosa richiede, e ti dice:
"Questa è urgente, ti propongo di rispondere così. Vuoi?"

L'agente fa lo stesso. Riceve eventi, li elabora, ti porta le opzioni già pronte.
Tu decidi. Lui esegue.
```

Implicazione pratica: **la chat è una feature avanzata, non il punto di ingresso primario**. Il punto di ingresso è l'**Agent Inbox** — una coda di situazioni che l'agente ha rilevato e per cui ha già elaborato opzioni.

### 5.2 Architettura: Tre Grafi LangGraph

```
GRAPH 1: TriageGraph          ← processa ogni evento in arrivo
GRAPH 2: WorkflowGraph        ← esegue un'azione specifica (avviata da inbox o da chat)
GRAPH 3: DailyDigestGraph     ← gira ogni mattina, produce il briefing giornaliero
```

I Workflow (v2.0 §5.2) restano ma cambiano ruolo: non sono l'entry point, sono i **building block** che `TriageGraph` e la chat chiamano per eseguire. Esempio: `draft_email_workflow`, `create_deadline_workflow`, `document_review_workflow`.

### 5.3 Event Types — Cosa Scatena il Triage

```python
class AgentEventType(str, Enum):
    DOCUMENT_UPLOADED   = "document_uploaded"    # upload via UI
    EMAIL_RECEIVED      = "email_received"        # forwarding SMTP o integrazione futura
    DEADLINE_APPROACHING = "deadline_approaching" # scheduler giornaliero
    DEADLINE_OVERDUE    = "deadline_overdue"
    USER_CHAT_MESSAGE   = "user_chat_message"     # messaggio diretto in chat
    MANUAL_TRIGGER      = "manual_trigger"        # utente preme "analizza questo"

@dataclass
class AgentEvent:
    event_id: str
    event_type: AgentEventType
    user_id: str
    payload: dict          # contenuto specifico per tipo
    received_at: datetime
    source_ref: str | None # es. document_id, email_id, deadline_id
```

### 5.4 TriageGraph

Questo grafo è leggero e veloce. Non esegue azioni — produce una `AgentInboxItem`.

```
START
  │
  ▼
[load_context]       Carica contesto utente rilevante (documenti correlati,
  │                  scadenze attive, storico interazioni con stessa entità)
  ▼
[analyze_event]      LLM analizza l'evento + contesto:
  │                  - Cosa sta succedendo?
  │                  - C'è un'azione richiesta implicita o esplicita?
  │                  - Qual è l'urgenza?
  │                  - Quali entità sono coinvolte? (importi, date, persone)
  ▼
[generate_options]   LLM genera 2-3 azioni suggerite, ordinate per rilevanza.
  │                  Per ogni azione: label human-readable, workflow_id da chiamare,
  │                  argomenti pre-compilati, risk_score stimato.
  │                  MAX 3 opzioni. Sempre l'opzione "Nessuna azione / Archivia".
  ▼
[classify_urgency]   immediate | today | this_week | low
  │                  Regole hard-coded (non LLM) per determinismo:
  │                  - deadline < 24h → immediate
  │                  - pagamento scaduto > 30gg → immediate
  │                  - deadline < 7gg → today
  │                  - tutto il resto → this_week o low via LLM
  ▼
[write_inbox_item]   Scrive su agent_inbox, invia notifica inapp
  │
  ▼
END
```

**Nota critica:** `TriageGraph` non usa strumenti rischiosi. Risk score massimo: 1 (solo lettura + scrittura interna). Non blocca mai su conferme. È sempre autonomo.

### 5.5 WorkflowGraph — Esecuzione di un'Azione

Avviato da:

- Utente che clicca un'azione suggerita in una `AgentInboxItem`
- Utente che scrive in chat qualcosa che corrisponde a un workflow noto
- Sistema (per azioni automatiche risk ≤ 2)

```
START (input: workflow_id + pre_filled_args + user_id)
  │
  ▼
[load_workflow_template]    Carica definizione workflow da WorkflowTemplateRegistry
  │
  ▼
[validate_args]             Verifica che gli argomenti pre-compilati siano completi.
  │                         Se mancano dati: chiedi all'utente SOLO quelli mancanti
  │                         (non re-chiedere tutto da zero).
  ▼
[execute_steps]             Esegue gli step del workflow in sequenza.
  │                         Stesso meccanismo di execute_loop (v2.0 §5.4):
  │                         risk ≤ 2 → auto | risk 3-4 → Review Card | risk 5 → refuse
  ▼
[report_result]             Aggiorna AgentInboxItem come "acted", notifica utente
  │
  ▼
END
```

### 5.6 Chat Agent — Invariato come Comportamento, Cambia il Ruolo

La chat non cambia internamente (v2.0 §5.4 `ChatAgentGraph` resta valido). Cambia il **contesto di uso**:

- **Uso primario:** utente vede inbox item → clicca azione → workflow parte. Zero chat.
- **Uso secondario:** utente vuole qualcosa che l'inbox non ha già proposto → scrive in chat.
- **Uso avanzato:** utente fa query complesse, analisi, richieste non standard.

Il `ChatAgentGraph` internamente tenta di mappare l'intent a un `workflow_id` noto (via `intent_classifier`). Se trova un match: lancia `WorkflowGraph` con gli argomenti che riesce a estrarre dal messaggio. Se non trova match: pianifica azioni custom come in v2.0.

### 5.7 WorkflowTemplateRegistry

```python
# app/agent/workflows/registry.py

@dataclass
class WorkflowTemplate:
    workflow_id: str
    name: str                      # "Invia sollecito pagamento"
    description: str               # usato dall'intent_classifier
    required_args: list[str]       # args che devono essere presenti
    optional_args: list[str]
    steps: list[WorkflowStep]      # sequenza di tool call con risk_score
    applicable_to: list[str]       # event_types a cui si applica naturalmente

WORKFLOW_REGISTRY = {
    "draft_payment_reminder": WorkflowTemplate(
        workflow_id="draft_payment_reminder",
        name="Sollecito pagamento",
        applicable_to=["deadline_overdue", "user_chat_message"],
        required_args=["invoice_id_or_client"],
        steps=[
            WorkflowStep(tool="search_documents", risk=1),   # trova fattura
            WorkflowStep(tool="draft_email", risk=3),         # genera bozza
            # send_email (risk 4) è step separato, avviato dopo approvazione bozza
        ]
    ),
    "process_document": WorkflowTemplate(...),
    "create_deadline_from_document": WorkflowTemplate(...),
    "reply_to_email": WorkflowTemplate(...),
    "generate_payment_status_report": WorkflowTemplate(...),
}
```

I template sono file Python in `app/agent/workflows/templates/`. Aggiungere un workflow = aggiungere un file. Nessuna modifica al core.

### 5.8 Agent State Schema — Aggiornato

```python
class AgentState(TypedDict):
    user_id: str
    session_id: str
    
    # Event origin (uno dei due è presente)
    triggering_event: AgentEvent | None     # se avviato da evento
    messages: Annotated[list, add_messages] # se avviato da chat
    
    # Workflow execution
    active_workflow_id: str | None
    workflow_args: dict
    planned_steps: list[PlannedAction]
    current_step_index: int
    
    # Results
    executed_steps: list[ExecutedAction]
    pending_confirmations: list[PendingConfirmation]
    inbox_item_id: str | None           # AgentInboxItem generata da questo run
    
    # Output
    final_response: str
    errors: list[str]
```

## 6. Action Classification & Risk System

### 6.1 Gerarchia delle Azioni

```
LIVELLO 0 — READ (Lettura pura)
  Esempi: ricerca documenti, visualizza scadenze, dashboard overview
  Esecuzione: autonoma, silent log
  
LIVELLO 1 — INTERNAL_WRITE (Scrittura interna, non esposta all'esterno)
  Esempi: archiviazione documento, tagging automatico, creazione scadenza ad alta confidence
  Esecuzione: autonoma, structured log con dettagli
  
LIVELLO 2 — EXTRACT_AND_CREATE (AI crea dati strutturati da input)
  Esempi: estrazione metadati da fattura, creazione deadline da contratto
  Condizione: esecuzione autonoma SOLO se confidence >= soglia configurabile
  Fallback: se confidence < soglia → LIVELLO 3 forzato
  
LIVELLO 3 — DRAFT (Prepara azione, non la esegue)
  Esempi: bozza email, bozza sollecito, riepilogo per approvazione
  Esecuzione: crea il draft, salva su DB, notifica utente → ATTENDE APPROVAZIONE
  
LIVELLO 4 — EXTERNAL_ACTION (Azione con effetti su sistemi/persone esterne)
  Esempi: invio email approvata, creazione evento calendario, eliminazione permanente
  Esecuzione: SEMPRE richiede approvazione esplicita, anche se l'utente "ha già confermato" in chat
  
LIVELLO 5 — FORBIDDEN (Vietato nel MVP, refuso a runtime)
  Esempi: invio a enti pubblici, modifiche gestionali, pagamenti, consigli fiscali interpretativi
  Esecuzione: IMPOSSIBILE. L'agente risponde con spiegazione del motivo.
```

### 6.2 Risk Scoring Engine

Il risk engine legge `app/agent/risk/rules.yaml`. Il file è **modificabile senza redeploy** (caricato all'avvio o con hot-reload).

```yaml
# app/agent/risk/rules.yaml
version: "1.0"

# Soglie confidence per estrazione AI
confidence_thresholds:
  document_classification: 0.80   # Sotto questa soglia: chiedi conferma tipo documento
  field_extraction: 0.85           # Sotto: chiedi conferma per ogni campo estratto
  deadline_extraction: 0.90        # Più alto: le scadenze sbagliate fanno danni
  amount_extraction: 0.92          # Importi: massima cautela

# Mapping tool → risk base
tool_risk_base:
  search_documents: 1
  get_document: 1
  list_deadlines: 1
  create_deadline: 2
  update_deadline: 2
  archive_document: 2
  draft_summary: 2
  draft_email: 3
  delete_deadline: 3
  send_email: 4
  create_calendar_event: 4
  delete_document: 4

# Modificatori di contesto (aggiungono +N al risk base)
context_modifiers:
  - condition: "action involves_external_party"
    add_risk: 1
  - condition: "action involves_monetary_amount"
    add_risk: 1
  - condition: "action involves_legal_document"
    add_risk: 1
  - condition: "action is_irreversible"
    add_risk: 1

# Soglie di comportamento
behavior:
  auto_execute_max_risk: 2         # Risk 1-2: esegui autonomamente
  require_preview_min_risk: 3      # Risk 3: mostra preview, chiedi conferma
  require_explicit_approval: 4     # Risk 4+: approvazione esplicita nel UI dedicato
  forbidden_risk: 5                # Sempre rifiutato

# Estensibilità futura: sostituire con modello ML
# risk_model:
#   enabled: false
#   model_path: "models/risk_classifier_v1.pkl"
#   fallback_to_rules: true
```

**Nota architetturale:** `RiskEngine` ha un metodo `compute_risk(action: PlannedAction, context: dict) -> int`. L'implementazione MVP legge `rules.yaml`. In futuro si può swappare con un classifier ML implementando la stessa interfaccia.

### 6.3 HITL Queue — Task State Machine

```
                    ┌─────────┐
                    │ PENDING │  (appena creato dal planner)
                    └────┬────┘
                         │ risk <= 2
                    ┌────▼────┐
                    │IN_PROGRESS│ (in esecuzione)
                    └────┬────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          ┌───────┐  ┌──────┐  ┌────────┐
          │ DONE  │  │FAILED│  │SKIPPED │ (dipendeva da pending)
          └───────┘  └──────┘  └────────┘

          risk >= 3: non passa da IN_PROGRESS

                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ risk >= 3
              ┌──────────▼──────────┐
              │ WAITING_CONFIRMATION │ (utente deve agire)
              └──┬──────────────────┘
                 │ approvato          │ rifiutato
          ┌──────▼─────┐        ┌────▼──────┐
          │  APPROVED  │        │ REJECTED  │
          └──────┬─────┘        └───────────┘
                 │ esecuzione
          ┌──────▼─────┐
          │   DONE     │
          └────────────┘
```

**Comportamento del loop:**

- L'agente itera la lista di `planned_actions`
- Se trova un'azione in `WAITING_CONFIRMATION`: la salta, aggiunge alle `skipped` tutte le azioni che hanno `depends_on` = questa azione
- Continua con la prossima azione indipendente
- Al termine: compone una risposta che riassume eseguito/pendente/saltato

**Ripresa dopo conferma:**

- Quando l'utente approva da UI: `POST /tasks/{confirmation_id}/approve`
- Il backend: marca l'azione APPROVED, ri-esegue il tool, aggiorna le azioni SKIPPED dipendenti → PENDING
- Se ci sono azioni PENDING ora eseguibili: le esegue (trigger async)
- Notifica inapp al termine

---

## 6.4 Review Card — Aggregazione per Documento

Quando `DocumentPipelineGraph` genera `PendingConfirmation` per più campi dello stesso documento, il frontend non mostra N card separate. Mostra **una sola Review Card** con tutti i campi estratti, differenziati visivamente per confidence.

### Schema Aggiuntivo

```sql
-- Aggiungere a pending_confirmations:
ALTER TABLE pending_confirmations
    ADD COLUMN group_id UUID,           -- stesso group_id = stessa Review Card
    ADD COLUMN group_type VARCHAR(100); -- "document_review" | "standalone"

-- Index per il frontend
CREATE INDEX ON pending_confirmations (group_id) WHERE group_id IS NOT NULL;
```

### Logica di Raggruppamento

```python
# In DocumentPipelineGraph, nodo confidence_gate:

async def confidence_gate(state: AgentState) -> AgentState:
    group_id = uuid4()  # tutte le conferme di questo documento condividono l'id
    
    for field_name, field_value in extracted_fields.items():
        confidence = field_confidences[field_name]
        threshold = risk_engine.get_threshold(field_name)
        
        if confidence < threshold:
            state.pending_confirmations.append(PendingConfirmation(
                group_id=group_id,
                group_type="document_review",
                field_name=field_name,
                extracted_value=field_value,
                confidence=confidence,
                # ...
            ))
    
    return state
```

### Comportamento Frontend della Review Card

```
📄 Revisione documento — fattura_mario_srl_maggio.pdf
────────────────────────────────────────────────────
Tipo documento    [Fattura           ]   ✓ 0.97 certo
Numero            [INV-2026-045      ]   ✓ 0.94 certo
Data emissione    [15/05/2026        ]   ✓ 0.91 certo
Data scadenza     [15/06/2026        ]   ⚠ 0.81 verifica  ← campo evidenziato
Importo netto     [2.400,00 €        ]   ✓ 0.96 certo
IVA               [528,00 €          ]   ✓ 0.95 certo
Fornitore         [Mario SRL         ]   ✓ 0.99 certo
P.IVA fornitore   [                  ]   ✗ non trovata   ← campo vuoto editabile

────────────────────────────────────────────────────
Crea scadenza di pagamento automaticamente?  [✓ Sì, 15/06/2026]

                      [Salta]   [Conferma]
```

- Campi ✓: non editabili di default (click per modificare)
- Campi ⚠: editabili e highlighted, focus automatico al primo
- Campi ✗: vuoti editabili, placeholder "inserisci manualmente"
- "Conferma" salva tutto e avanza il workflow

---

## 6.5 Trust Progressivo — Schema e Interfaccia (implementazione Phase 3)

**Lo schema DB va aggiunto in Phase 0 per non fare migration tardiva. Il RiskEngine lo usa solo da Phase 3.**

```sql
CREATE TABLE user_extraction_trust (
    user_id UUID NOT NULL REFERENCES users(id),
    document_type VARCHAR(100) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    total_extractions INTEGER DEFAULT 0,
    confirmed_without_edit INTEGER DEFAULT 0,  -- utente ha confermato senza modificare
    edited_extractions INTEGER DEFAULT 0,       -- utente ha corretto il valore
    accuracy FLOAT GENERATED ALWAYS AS (
        confirmed_without_edit::float / NULLIF(total_extractions, 0)
    ) STORED,
    last_updated TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, document_type, field_name)
);
```

Viene aggiornata ogni volta che l'utente interagisce con una Review Card:

- Conferma senza modificare → `confirmed_without_edit += 1`
- Modifica il valore → `edited_extractions += 1`
- In entrambi i casi → `total_extractions += 1`

Il `RiskEngine` la usa solo dopo Phase 3. In Phase 0-2: la tabella esiste, viene popolata, ma `effective_threshold()` ignora i dati e usa la soglia base.

---

## 7. Document Processing Pipeline

### 7.1 Parser Assignment per Tipo File

Ogni parser implementa `DocumentParserPort`. Al momento dell'upload, il `ParserRegistry` seleziona il parser corretto tramite `can_parse()`.

|Content-Type|Filename pattern|Parser primario|Parser fallback|Note|
|---|---|---|---|---|
|`application/pdf`|`*.pdf`|LlamaParse|Unstructured.io|LlamaParse per PDF strutturati, Unstructured per scansioni|
|`application/vnd.ms-excel`|`*.xls`|Unstructured.io|pandas||
|`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`|`*.xlsx`|Unstructured.io|pandas||
|`text/csv`|`*.csv`|pandas|—|Parsing diretto, no AI needed|

**MVP supporta solo questi formati.** Upload di altri formati → errore `415 Unsupported Media Type` con messaggio chiaro.

### 7.2 Parser Fallback Logic

```python
class ParserWithFallback:
    """Tenta il parser primario, cade sul fallback se confidence < 0.60"""
    
    async def parse(self, file: bytes, filename: str) -> ParsedDocument:
        result = await self.primary.parse(file, filename)
        if result.confidence < 0.60 and self.fallback:
            fallback_result = await self.fallback.parse(file, filename)
            # Usa il risultato con confidence più alta
            return max(result, fallback_result, key=lambda r: r.confidence)
        return result
```

### 7.3 Extraction Fields per Tipo Documento

Il modello LLM usa prompt specializzati per tipo documento. Il tipo è determinato dal `classify_document` node del pipeline graph.

**Fattura:**

- `numero_fattura`, `data_emissione`, `data_scadenza`, `importo_lordo`, `importo_iva`, `importo_netto`, `fornitore_nome`, `fornitore_piva`, `cliente_nome`, `cliente_piva`

**Contratto:**

- `tipo_contratto`, `data_firma`, `data_inizio`, `data_scadenza`, `data_rinnovo_tacito`, `parti`, `oggetto`, `importo_annuale`, `clausole_recesso`

**Nota Spese:**

- `data`, `dipendente`, `voci` (lista: descrizione, importo, categoria), `totale`, `stato_rimborso`

**Documento generico:**

- `titolo`, `data_documento`, `tipo_stimato`, `parti_coinvolte`, `date_rilevanti`

---

## 8. Storage Layer

### 8.1 File Storage — Tre Implementazioni

Il provider attivo è selezionato da `FILE_STORAGE_BACKEND` env var.

|Valore env|Adapter|Quando usarlo|
|---|---|---|
|`local`|`LocalStorageAdapter`|Dev locale, CI, testing|
|`minio`|`MinIOAdapter`|Self-hosted (Docker Compose)|
|`s3`|`S3Adapter`|Cloud hosted|

`LocalStorageAdapter` salva in `/tmp/acg_storage/{user_id}/`. Funziona senza configurazione. **Non usare in produzione.**

`MinIOAdapter` e `S3Adapter` implementano lo stesso Protocol con boto3. La differenza è solo l'endpoint URL. Configurazione via:

```
FILE_STORAGE_BACKEND=minio
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=acg-documents

# oppure
FILE_STORAGE_BACKEND=s3
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=acg-documents
```

**Struttura path:** `{user_id}/{year}/{month}/{file_id}_{original_filename}`

**Multi-tenancy futura:** `[DEFERRED]` — Quando aggiunto, il path diventa `{tenant_id}/{user_id}/...`. Lo switch è in un unico punto: `build_storage_key()` in `LocalStorageAdapter` (e equivalenti).

### 8.2 Vector Store

PostgreSQL + pgvector. Un'unica tabella `document_chunks` con `user_id` per isolation (RLS `[DEFERRED]` — nell'MVP filtro manuale in query).

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),          -- OpenAI ada-002 / Anthropic compatible
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX ON document_chunks (user_id);
```

Embedding model: `text-embedding-3-small` (OpenAI) o equivalente Anthropic. Configurabile via `EMBEDDING_MODEL` env var. Il `VectorStorePort` accetta testo e gestisce internamente l'embedding.

---

## 9. LLM Provider — Primary + Fallback Chain

### 9.1 Provider Stack

```
PRIMARY:     Anthropic Claude (claude-sonnet-4-5 o superiore)
FALLBACK 1:  OpenAI GPT-4o
FALLBACK 2:  Google Gemini 1.5 Pro
FALLBACK 3:  [opzionale] Mistral Large (se configurato)
```

### 9.2 Fallback Triggers

```python
# app/agent/llm/fallback_chain.py

FALLBACK_TRIGGERS = {
    "api_error": True,              # Qualsiasi 5xx dal provider
    "timeout_seconds": 45,          # Request timeout
    "rate_limit": True,             # 429 Too Many Requests
    "provider_down": True,          # Connection refused / DNS fail
    "context_too_long": True,       # 413 / context length exceeded → prova provider con context più grande
}

# Sequenza: prova PRIMARY, se fallback trigger → prova FALLBACK_1, poi FALLBACK_2, poi FALLBACK_3
# Se tutti falliscono: ritorna errore all'utente con messaggio chiaro
# Log ogni fallback con motivo
```

### 9.3 Prompt Compatibility

I prompt sono scritti per essere **model-agnostic**. Nessun prompt usa feature proprietarie di un singolo provider. I system prompt sono file `.md` in `app/agent/prompts/`. Non hardcodare prompt nel codice Python.

---

## 10. Guardrails & Safety Constitution

### 10.1 Architettura a Tre Livelli

```
LIVELLO 1 — INPUT GUARDRAILS (prima che l'agente veda il messaggio)
  - PII detection: CF, P.IVA, IBAN, coordinate bancarie → redact o flag
  - Jailbreak/prompt injection detection: pattern matching + LLM classifier leggero
  - Topic restriction: messaggio fuori scope? → rifiuto cortese
  - Blacklist check: richiesta in FORBIDDEN list? → rifiuto immediato

LIVELLO 2 — EXECUTION GUARDRAILS (durante LangGraph)
  - Risk engine su ogni action (vedi sezione 6)
  - HITL gate su ogni action rischiosa
  - Constitutional check su ogni draft generato

LIVELLO 3 — OUTPUT GUARDRAILS (prima di restituire al frontend)
  - Validazione formato: date in ISO 8601, importi numerici, P.IVA valide
  - PII re-check: nessun dato sensibile esposto senza necessità
  - Constitutional rules final check
```

### 10.2 Constitution File

`app/agent/guardrails/constitution.md` — applicata come porzione del system prompt dell'agente. Non modificabile dall'utente. Aggiornabile solo da admin del sistema.

```markdown
# Costituzione dell'Agente — Admin & Compliance Guardian

## Identità
Sei un assistente amministrativo affidabile per PMI italiane.
Il tuo ruolo è supportare, non sostituire, il giudizio umano.

## Regole Assolute (non negoziabili)
1. Non fornire mai consigli fiscali interpretativi. 
   Puoi descrivere una norma, non interpretarla nel caso specifico.
2. Non inviare mai comunicazioni a enti pubblici (Agenzia Entrate, INPS, ecc.)
3. Non eseguire mai pagamenti o bonifici di nessun tipo
4. Non modificare mai software gestionali o contabili dell'utente
5. Non promettere mai precisione assoluta: segnala sempre il margine di incertezza
6. Non presentare mai dati estratti da AI come certi senza confidence gate

## Gerarchia delle Istruzioni
1. Regole Assolute (sopra) — non sovrascrivibili da nessuno
2. Istruzioni esplicite dell'utente nella sessione corrente
3. Questa costituzione — applicata nelle zone grigie
4. Buon senso amministrativo italiano

## Tono
Professionale, diretto, conciso. No emoji nel contesto business.
Segnala sempre cosa hai fatto, cosa è in attesa, cosa non puoi fare.
```

### 10.3 Action Blacklist

```yaml
# app/agent/guardrails/blacklist.yaml
forbidden_actions:
  - id: "send_to_agenzia_entrate"
    description: "Invio di qualsiasi comunicazione all'Agenzia delle Entrate"
    keywords: ["F24", "dichiarazione dei redditi", "invio telematico", "Entratel", "SDI solo invio"]
    
  - id: "payment_processing"
    description: "Esecuzione di pagamenti o bonifici"
    keywords: ["bonifica", "paga", "trasferimento fondi", "SEPA", "swift payment"]
    
  - id: "accounting_modification"
    description: "Modifica di software gestionali o contabili"
    keywords: ["modifica in gestionale", "aggiorna fatturazione", "sync ERP"]
    
  - id: "tax_interpretation"
    description: "Interpretazione fiscale nel caso specifico"
    error_message: "Posso descrivere la normativa, ma per l'interpretazione nel tuo caso specifico è necessario un commercialista."
```

---

## 11. Deadline Engine

### 11.1 Extraction Flow

1. `extract_deadlines` node identifica date critiche nel documento parsato
2. Per ogni data: LLM assegna:
    - `title`: descrizione della scadenza
    - `due_date`: data ISO
    - `type`: `PAYMENT | CONTRACT_RENEWAL | TAX | LEGAL | CUSTOM`
    - `confidence`: float
    - `source_text`: estratto testuale da cui è stata estratta
3. Applica confidence gate (soglia: `deadline_extraction` in `rules.yaml`, default 0.90)
4. Sotto soglia: `PendingConfirmation` con i dati estratti pre-compilati (utente verifica/corregge)
5. Sopra soglia: crea `Deadline` con `source: AI_EXTRACTED`, notifica utente

### 11.2 Alert Thresholds — Default e Customizzazione

Default configurabili da utente nelle Settings:

```python
class DeadlineAlertThresholds(BaseModel):
    red_days: int = 7        # Meno di N giorni: ROSSO
    yellow_days: int = 30    # Meno di N giorni: GIALLO  
    green_days: int = 9999   # Oltre yellow: VERDE
    
    # Notifiche preventive
    notify_days_before: list[int] = [30, 7, 3, 1]  # Invia notifica N giorni prima
    
    # Canali per urgenza
    red_channels: list[str] = ["inapp", "email"]
    yellow_channels: list[str] = ["inapp"]
    green_channels: list[str] = []
```

### 11.3 Recurrence

```python
class RecurrenceRule(str, Enum):
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"       # Trimestrale (IVA, INPS, ecc.)
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"             # cron expression in custom_cron field
```

Il `DeadlineScheduler` gira ogni giorno alle 08:00 (cron job via `APScheduler` o task Celery). Calcola deadline in scadenza nelle prossime 24h e nei prossimi `notify_days_before` giorni. Dispatcha notifiche via `NotifierPort`.

---

## 11bis. Daily Digest & Proactive Scheduler

### Principio

Il `DailyDigestGraph` non aspetta che l'utente apra l'app. Ogni mattina alle 08:00 genera un `AgentInboxItem` di tipo `daily_digest` con la situazione della giornata. È l'equivalente di un assistente che ti aspetta in ufficio con un foglio: "Ecco cosa c'è oggi."

### DailyDigestGraph

```
START (triggered by APScheduler, 08:00 ogni giorno)
  │
  ▼
[collect_situation]       Query DB — nessun LLM:
  │                       - deadline overdue (status=active, due_date < oggi)
  │                       - deadline urgenti (due_date tra oggi e +7gg)
  │                       - deadline questa settimana (+7gg a +30gg)
  │                       - documenti in pending_review
  │                       - bozze email in attesa
  │                       - inbox items non risolti da >48h
  ▼
[detect_patterns]         LLM leggero — analizza la situazione complessiva:
  │                       - C'è qualcosa di insolito? (cliente che non paga da 60gg)
  │                       - C'è un'opportunità di ottimizzazione?
  │                         (4 solleciti da mandare → mandarli in batch)
  │                       - Suggerimento proattivo del giorno (max 1)
  ▼
[compose_digest]          Genera il testo del digest (template Jinja2 + LLM per
  │                       il paragrafo "suggerimento del giorno")
  │                       Struttura fissa, contenuto variabile.
  ▼
[write_inbox_item]        Inserisce in agent_inbox con:
  │                       event_type = "daily_digest"
  │                       urgency = "immediate" (va sempre in cima)
  │                       expires_at = oggi mezzanotte
  ▼
[send_email_digest]       Se utente ha abilitato digest email:
  │                       invia versione email del digest (template HTML)
  ▼
END
```

### Struttura del Digest

```
Buongiorno — Venerdì 30 maggio

━━━ Attenzione immediata ━━━━━━━━━━━━━━━━
🔴  Fattura INV-034 (Mario SRL) — scaduta 8 giorni, €3.400
    [Invia sollecito]

🔴  Contratto Logistics SpA — rinnovo tacito tra 12 giorni
    [Gestisci rinnovo]

━━━ Da fare questa settimana ━━━━━━━━━━━━
🟠  3 documenti caricati martedì — revisione pendente
    [Rivedi ora]

🟠  Contributi INPS — scadenza 16 giugno (17 giorni)
    [Segna come gestita]

━━━ Tutto il resto in ordine ━━━━━━━━━━━━
🟢  5 scadenze nei prossimi 30 giorni — nessuna critica

━━━ Suggerimento del giorno ━━━━━━━━━━━━
Hai 4 fatture emesse non saldate da oltre 30 giorni (tot. €11.200).
Vuoi che prepari i solleciti in blocco così li rivedi e invii tutti insieme?
[Prepara batch solleciti]  [Ignora]
```

### Implementazione Tecnica — Semplice e Scalabile

```python
# app/services/daily_digest_service.py

class DailyDigestService:
    """
    Genera il digest giornaliero.
    Dipende solo da: DeadlineRepository, InboxRepository, LLMProvider.
    Nessuna dipendenza da LangGraph — usa i service layer direttamente.
    """
    
    async def generate_for_user(self, user_id: str) -> AgentInboxItem:
        # 1. Collect (puro DB, nessun LLM)
        situation = await self._collect_situation(user_id)
        
        # 2. Detect patterns (LLM leggero, max 200 token output)
        suggestion = await self._detect_patterns(situation)
        
        # 3. Compose (template + suggestion)
        digest_text = self._render_digest(situation, suggestion)
        suggested_actions = self._build_actions(situation)
        
        # 4. Write inbox item
        return await self.inbox_repo.create(AgentInboxItem(
            user_id=user_id,
            event_type="daily_digest",
            agent_analysis=digest_text,
            urgency="immediate",
            suggested_actions=suggested_actions,
            expires_at=end_of_today()
        ))
    
    async def generate_for_all_users(self):
        """Chiamato dallo scheduler. Processa utenti in sequenza con rate limiting."""
        users = await self.user_repo.get_active_users()
        for user in users:
            try:
                await self.generate_for_user(user.id)
            except Exception as e:
                log.error("digest_failed", user_id=user.id, error=str(e))
                # Non blocca gli altri utenti
```

**Scalabilità futura:** sostituire il loop sequenziale con una coda di task (Celery/ARQ). Il `DailyDigestService` rimane invariato — cambia solo il caller.

---

## 12. Email Drafting System

### 12.1 Draft States

```
CREATED → PENDING_REVIEW → APPROVED → SENT
                         ↘ REJECTED
```

### 12.2 Flow

1. Agente riceve richiesta (es. "genera sollecito per fattura 123 in scadenza")
2. `draft_email` tool (risk: 3) genera `EmailDraft` con LLM
3. `EmailDraft` salvata su DB con stato `PENDING_REVIEW`
4. `PendingConfirmation` creata → utente notificato
5. Utente apre UI: vede preview con to/subject/body editabile
6. Utente approva (con o senza modifiche) → stato `APPROVED`
7. Backend esegue `send_email` tool (risk: 4) → richiede seconda conferma esplicita
8. Email inviata via `EmailSenderPort` → stato `SENT`

> **Due step di conferma per l'invio:** il draft è un'approvazione del contenuto. L'invio reale è un'azione separata con il suo `PendingConfirmation`. Questo protegge da invii accidentali dopo approvazione del testo.

### 12.3 SMTP Configuration

```
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=noreply@azienda.it
SMTP_TLS=true
```

Template email in `app/templates/email/` (Jinja2). Template separati per: sollecito_pagamento, notifica_scadenza, notifica_documento, conferma_azione.

---

## 13. Notification System

### 13.1 In-App Notifications

Tabella `notifications` in DB. Frontend fa polling ogni 30s o usa WebSocket (decisione implementativa, polling va bene per MVP).

```python
class NotificationLevel(str, Enum):
    INFO = "info"       # Documento archiviato, scadenza creata
    WARNING = "warning" # Scadenza in arrivo (giallo)
    URGENT = "urgent"   # Scadenza imminente (rosso)
    ACTION = "action"   # Richiede azione utente (conferma pendente)
```

### 13.2 Notification Routing

```python
# NotificationDispatcher: decide canali in base a level + preferenze utente
async def dispatch(self, user_id: str, level: NotificationLevel, ...):
    thresholds = await self.get_user_thresholds(user_id)
    channels = thresholds.get_channels_for_level(level)
    
    tasks = []
    if "inapp" in channels:
        tasks.append(self.inapp_notifier.send_inapp(...))
    if "email" in channels:
        tasks.append(self.email_notifier.send_email_notification(...))
    
    await asyncio.gather(*tasks)
```

---

## 14. Database Schema

```sql
-- Utenti (gestito da Clerk in cloud, dummy table in self-hosted)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'owner',    -- owner | admin | viewer [DEFERRED: RBAC]
    notification_settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
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
    document_type VARCHAR(100),          -- fattura | contratto | nota_spese | altro
    document_type_confidence FLOAT,
    extracted_metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    parse_status VARCHAR(50) DEFAULT 'pending',  -- pending | parsed | failed
    created_at TIMESTAMPTZ DEFAULT now(),
    archived_at TIMESTAMPTZ
);

-- Chunk vettoriali (con pgvector)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

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
    source_text TEXT,                      -- estratto testuale usato per estrazione
    created_at TIMESTAMPTZ DEFAULT now(),
    notified_at JSONB DEFAULT '[]'         -- array di { days_before, notified_at }
);

-- Task Agent (unit of work)
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id VARCHAR(255),
    action_type VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100),
    tool_args JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',  -- pending | in_progress | waiting_confirmation | approved | done | failed | skipped | rejected
    risk_score INTEGER NOT NULL,
    depends_on_task_id UUID REFERENCES agent_tasks(id),
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Conferme HITL
CREATE TABLE pending_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES agent_tasks(id),
    user_id UUID NOT NULL REFERENCES users(id),
    description TEXT NOT NULL,            -- Human-readable: "Vuoi creare scadenza X?"
    data_for_review JSONB NOT NULL,        -- Dati pre-compilati per revisione
    risk_level VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending | approved | rejected
    user_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- Bozze Email
CREATE TABLE email_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    task_id UUID REFERENCES agent_tasks(id),
    to_addresses TEXT[] NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending_review',  -- pending_review | approved | sent | rejected
    approved_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Notifiche In-App
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    body TEXT,
    level VARCHAR(50) NOT NULL,          -- info | warning | urgent | action
    related_type VARCHAR(100),           -- deadline | document | confirmation | email_draft
    related_id UUID,
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit Log (append-only)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    action_type VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100),
    input_summary TEXT,                  -- Riassunto (non dati sensibili grezzi)
    output_summary TEXT,
    risk_score INTEGER,
    status VARCHAR(50),
    llm_model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tenancy [DEFERRED]
-- La colonna tenant_id è prevista su tutte le tabelle ma non implementata nell'MVP.
-- Lasciare un commento -- [TODO: multi-tenancy] su ogni tabella.
```

---

## 14bis. Agent Inbox — Schema e API

### Schema DB

```sql
CREATE TABLE agent_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Evento che ha generato questo item
    event_type VARCHAR(100) NOT NULL,
    event_source JSONB NOT NULL,       -- { type, from, subject, document_id, ... }
    source_ref_id UUID,                -- document_id / deadline_id / email_id se applicabile
    
    -- Analisi agente
    agent_analysis TEXT NOT NULL,       -- testo human-readable: cosa l'agente ha capito
    urgency VARCHAR(50) NOT NULL,       -- immediate | today | this_week | low
    
    -- Azioni suggerite (max 3 + "dismiss")
    -- [ { id, label, workflow_id, pre_filled_args, risk_score, estimated_seconds } ]
    suggested_actions JSONB NOT NULL,
    
    -- Stato
    status VARCHAR(50) DEFAULT 'pending', -- pending | acted | dismissed | expired
    chosen_action_id VARCHAR(100),
    chosen_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ              -- NULL = non scade. Daily digest scade a mezzanotte.
);

CREATE INDEX ON agent_inbox (user_id, status, urgency, created_at DESC);
```

### API Endpoints (aggiungere a §15)

```
AGENT INBOX
  GET    /inbox                       Lista items (filtro: status, urgency)
  GET    /inbox/unread-count          Count per badge header
  POST   /inbox/{id}/act              Esegui azione suggerita { action_id }
  POST   /inbox/{id}/dismiss          Segna come gestito manualmente
  POST   /inbox/trigger-triage        Forza triage manuale su un evento (dev/debug)
```

### Frontend: InboxCard Component

Ogni `AgentInboxItem` si renderizza come una card. Design principi:

- L'analisi dell'agente è **compatta** (max 2 righe). Se l'utente vuole dettagli: expand.
- I bottoni delle azioni usano **verb specifici**, non generici. Non "Esegui" ma "Invia sollecito" / "Concedi proroga" / "Rifiuta cortese".
- Il bordo sinistro della card è colorato per urgency: rosso / arancio / grigio.
- Azione al click su bottone ad alto risk: apre preview/bozza — non esegue direttamente.

```
┌─────────────────────────────────────────────────────┐
│ 🔴 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                     │
│  📧 Email — marco.rossi@clienti.it                  │
│  "Richiesta proroga pagamento fattura maggio"        │
│                                                     │
│  Richiesta di proroga su INV-045 (€2.928, scaduta   │
│  5 giorni fa). Cliente abituale, prima richiesta.   │
│                                                     │
│  [Concedi 15gg]  [Rifiuta cortese]  [Rimanda]  [✕] │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 🟠 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                     │
│  📄 Contratto — Fornitore Logistics SpA             │
│  Rinnovo tacito tra 12 giorni (16 giugno)           │
│                                                     │
│  Contratto annuale €8.400. Clausola recesso:        │
│  15 giorni prima del rinnovo.                       │
│                                                     │
│  [Prepara disdetta]  [Rinnova]  [Ricordamelo dopo] │
└─────────────────────────────────────────────────────┘
```

### Dashboard Layout Aggiornato

Il dashboard non è più "semaforo + attività recente". È **Inbox-first**:

```
┌──────────────────────────────────────────────────────────────┐
│  🔴 2   🟠 1   🟢 5        🔍 Cerca…        🔔 3  [avatar] │
├──────────────────────────────────────────────────────────────┤
│                                              │               │
│   Agent Inbox                               │  Scadenze     │
│   ──────────────────────────────            │  ─────────    │
│   [Daily Digest Card — oggi]                │  🔴  2        │
│   [Card urgente 1]                          │  🟠  1        │
│   [Card urgente 2]                          │  🟢  5        │
│   [Card this_week 1]                        │               │
│                                             │  Prossima:    │
│   💬 Chiedimi qualcosa…                     │  16 giu INPS  │
│                                             │               │
└──────────────────────────────────────────────────────────────┘
```

---

## 15. API Design (FastAPI v1)

Tutte le route sotto `/api/v1/`. Auth via JWT header `Authorization: Bearer <token>`.

```
DOCUMENTS
  POST   /documents/upload          Carica documento, avvia pipeline asincrona
  GET    /documents                 Lista documenti utente (paginata, filtrata)
  GET    /documents/{id}            Dettaglio + metadati estratti
  GET    /documents/{id}/download   Download file originale
  DELETE /documents/{id}            Archivia (soft delete) — risk 4, crea PendingConfirmation
  POST   /documents/search          Ricerca semantica { query, filters }

DEADLINES
  GET    /deadlines                 Lista con filtri (status, type, date range)
  POST   /deadlines                 Crea manualmente
  PUT    /deadlines/{id}            Modifica
  DELETE /deadlines/{id}            Cancella — crea PendingConfirmation
  GET    /deadlines/upcoming        Prossime N scadenze per dashboard

AGENT
  POST   /agent/query               Chat con l'agente { message, session_id }
  GET    /agent/sessions/{id}       Stato di una sessione (azioni eseguite, pending)
  GET    /agent/tasks               Task utente (attivi, completati)

HITL
  GET    /confirmations             Lista conferme pendenti
  POST   /confirmations/{id}/approve  Approva con dati facoltativamente modificati
  POST   /confirmations/{id}/reject   Rifiuta con commento opzionale

EMAIL DRAFTS
  GET    /email-drafts              Lista bozze
  GET    /email-drafts/{id}         Dettaglio bozza
  PUT    /email-drafts/{id}         Modifica bozza (solo se PENDING_REVIEW)
  POST   /email-drafts/{id}/approve Approva bozza → crea nuovo PendingConfirmation per invio
  POST   /email-drafts/{id}/send    Invia bozza approvata (richiede approvazione previa)
  DELETE /email-drafts/{id}         Cancella bozza

NOTIFICATIONS
  GET    /notifications             Lista notifiche (unread first)
  POST   /notifications/{id}/read   Marca come letta
  POST   /notifications/read-all    Marca tutte come lette

DASHBOARD
  GET    /dashboard/overview        Semaforo scadenze, contatori, attività recente

AUDIT
  GET    /audit-log                 Log azioni (paginato, filtrato per tipo/data)

SETTINGS
  GET    /settings                  Preferenze utente (soglie, canali notifiche)
  PUT    /settings                  Aggiorna preferenze
```

---

## 16. Frontend Architecture

### 16.1 Stack

React 19 + TypeScript + Vite + shadcn/ui + TailwindCSS + React Query (server state) + Zustand (UI state).

### 16.2 Pagine

|Route|Componente|Descrizione|
|---|---|---|
|`/`|`DashboardPage`|Semaforo scadenze, documenti recenti, feed attività, conferme pendenti|
|`/documents`|`DocumentsPage`|Lista, search, upload, preview|
|`/documents/:id`|`DocumentDetailPage`|Metadati estratti, scadenze correlate, audit|
|`/deadlines`|`DeadlinesPage`|Calendario + lista, filtri, crea manuale|
|`/agent`|`AgentPage`|Chat con l'agente, storico sessioni|
|`/confirmations`|`ConfirmationsPage`|HITL queue: lista e action per ogni conferma pendente|
|`/email-drafts`|`EmailDraftsPage`|Lista bozze con preview e approvazione|
|`/audit`|`AuditPage`|Log azioni (read-only)|
|`/settings`|`SettingsPage`|Soglie notifiche, SMTP, preferenze|

### 16.3 Componenti Chiave

**`DeadlineSemaphore`**: widget dashboard. Tre colonne (rosso/giallo/verde) con count e lista compatta. Clic su una colonna → naviga a `/deadlines` filtrata.

**`ConfirmationCard`**: card per ogni `PendingConfirmation`. Mostra descrizione human-readable, dati estratti editabili in-place, pulsanti Approva / Rifiuta. Usata sia nella page dedicata che come badge nel layout.

**`AgentChatInterface`**: chat standard. Ogni messaggio mostra lo stato delle azioni: badge per azioni eseguite, link a conferme create, errori inline.

**`DocumentUploadZone`**: drag & drop. Supporta pdf/xlsx/xls/csv. Mostra progress del parsing. Al termine: redirect a `DocumentDetailPage`.

**`EmailDraftPreview`**: preview HTML dell'email con editor inline per modifiche pre-approvazione.

**Layout:**

- Sidebar sinistra: navigazione, badge notifiche
- Header: ricerca globale, campanella notifiche, profilo
- Il badge notifiche campanella mostra count di `ACTION`-level notifications (conferme pendenti, bozze in attesa)

---

## 17. Development Phases — Aggiornate

### Phase 0 — Foundation (Settimana 1)

_Invariata rispetto a v2.0, con aggiunta:_

- [ ] Schema `agent_inbox` e `user_extraction_trust` nelle migrations (anche se non usati)
- [ ] `WorkflowTemplateRegistry` stub con 0 template (struttura pronta)

### Phase 1 — Document Core (Settimane 2-4)

_Invariata rispetto a v2.0, con aggiunta:_

- [ ] `TriageGraph` funzionante per eventi `DOCUMENT_UPLOADED`
    - Nessuna analisi LLM avanzata — solo classificazione documento e campi estratti
    - Genera Review Card aggregata (group_id)
- [ ] `AgentInboxItem` scritto su DB dopo ogni upload
- [ ] Frontend: `InboxCard` component base, dashboard inbox-first layout

**Deliverable Phase 1:** Upload PDF → Review Card aggregata in inbox → conferma → documento archiviato.

### Phase 2 — Intelligence + Inbox (Settimane 5-7)

_Modifica rispetto a v2.0: più focus su inbox e triage, meno su chat agent raw._

- [ ] `TriageGraph` completo per tutti gli event types
- [ ] `WorkflowGraph` con primi 3 template: `draft_payment_reminder`, `process_document`, `create_deadline_from_document`
- [ ] `DailyDigestService` + scheduler 08:00 (senza LLM avanzato: solo template strutturato)
- [ ] `InboxCard` completa con tutti gli stili urgency
- [ ] Chat agent che mappa intent → workflow template
- [ ] Deadline engine + notification system (invariato da v2.0)
- [ ] Email drafting con SMTP (invariato da v2.0)
- [ ] Guardrails layer (invariato da v2.0)

**Deliverable Phase 2:** Daily digest ogni mattina. Email ricevuta → triage → card in inbox → azione in 2 click. Chat funzionante per query avanzate.

### Phase 3 — Polish, Trust & Production (Settimane 8-10)

- [ ] Trust progressivo: `RiskEngine.effective_threshold()` legge `user_extraction_trust`
- [ ] `detect_patterns()` nel digest con LLM (suggerimento del giorno)
- [ ] Workflow template aggiuntivi: `reply_to_email`, `generate_payment_status_report`, `batch_send_reminders`
- [ ] Digest email opzionale (versione HTML via SMTP)
- [ ] LangSmith tracing
- [ ] Testing con dataset realistico
- [ ] Security review
- [ ] Docker Compose production-ready
- [ ] Google Calendar adapter (stretch)
- [ ] Documentazione API

## 18. Technical Debt Register

Decisioni consapevolmente rimandate. Ogni voce ha un tag `[TODO: <id>]` nel codice.

|ID|Cosa|Dove|Note|
|---|---|---|---|
|`TD-001`|Multi-tenancy RLS|Tutte le tabelle DB + tutti gli adapter|Aggiunge `tenant_id` a ogni query. Stub: filtro solo per `user_id`|
|`TD-002`|n8n integration|`adapters/automation/` non esiste|Porta `AutomationPort` da aggiungere. n8n per email/calendar triggers futuri|
|`TD-003`|ML Risk Scoring|`agent/risk/engine.py`|Sezione commentata in `rules.yaml`. Sostituisce rules-based con modello trained|
|`TD-004`|Feedback loop|`api/v1/feedback.py` non esiste|Tabella `llm_feedback` da aggiungere. Pipeline review → fine-tuning/prompt improvement|
|`TD-005`|White-label theming|Frontend CSS variables|Design token system pronto, switching non implementato|
|`TD-006`|RBAC avanzato|`users.role` solo stringa|Roles: owner/admin/viewer/approver. Policy engine da aggiungere|
|`TD-007`|Billing/subscription|Non esiste|Usage metering necessario prima del lancio commercial|
|`TD-008`|File encryption at rest|Storage adapters|MinIO/S3 server-side encryption: aggiungere flag in configurazione|
|`TD-009`|Mobile app|Non esiste|PWA come primo step|
|ID|Cosa|Note||
|----|------|------||
|`TD-010`|Email receiving nativo|SMTP inbound (Postal/Mailgun inbound) per catturare email direttamente senza forwarding manuale||
|`TD-011`|Workflow template via UI|Attualmente i template sono file Python. In futuro: editor no-code per creare workflow custom||
|`TD-012`|Digest personalizzazione|Formato e contenuto digest fisso nell'MVP. Futuro: utente sceglie cosa includere||
|`TD-013`|Pattern detection avanzata|`detect_patterns()` usa LLM leggero. Futuro: modello trained su dati storici dell'utente||

---

## 19. Note Implementative per AI Coding Assistant

Queste istruzioni sono per chi implementa questo progetto.

### Ordine di implementazione raccomandato

1. **Prima: Protocol + dummy adapter**. Non scrivere codice applicativo prima che tutti i Protocol esistano e abbiano un dummy funzionante. I test devono girare con dummy prima ancora di toccare LangGraph.
    
2. **LangGraph: parti semplice**. Implementa `DocumentPipelineGraph` come sequenza lineare di nodi prima di aggiungere conditional edges. Aggiungi la branching logic (confidence gate) solo quando la sequenza base funziona.
    
3. **Risk engine: prima hardcoded, poi YAML**. Implementa `compute_risk()` con i valori hardcoded in Python. Solo quando funziona, sposta la config in `rules.yaml`.
    
4. **HITL: implementa la state machine prima dell'UI**. La logica DB (task states, transitions) deve essere testata prima di toccare il frontend.
    

### Convenzioni di codice

- Pydantic v2 per tutti i modelli di dominio e API schema
- `async/await` ovunque (FastAPI + asyncpg + async LangGraph)
- Nessun `print()` nel codice: solo `logging` strutturato con `structlog`
- Ogni service ha un `logger = structlog.get_logger(__name__)`
- Log format: `{"event": "...", "user_id": "...", "action": "...", "risk_score": N}`
- Type hints su tutto: `mypy --strict` deve passare
- Ogni Protocol ha almeno un test che verifica l'interfaccia con un dummy

### Cosa NON fare

- Non usare `global state` nell'agent. Tutto passa attraverso `AgentState`
- Non hardcodare prompt nel codice Python. Sempre file `.md` in `app/agent/prompts/`
- Non accedere al DB direttamente nei nodi LangGraph. Sempre via service layer
- Non lanciare eccezioni non tipizzate. Definire `ACGException` base e sottoclassi
- Non fare retry automatici su azioni di `LIVELLO 4+`. Solo l'utente può ri-approvare

### Environment Variables — Schema Completo

```bash
# === CORE ===
ENVIRONMENT=development              # development | staging | production
SECRET_KEY=...                       # JWT signing key
DATABASE_URL=postgresql+asyncpg://...

# === FILE STORAGE ===
FILE_STORAGE_BACKEND=local           # local | minio | s3

# local (dev only)
LOCAL_STORAGE_PATH=/tmp/acg_storage

# minio
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=acg-documents

# s3
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=acg-documents

# === LLM ===
LLM_PRIMARY_PROVIDER=anthropic       # anthropic | openai | gemini
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...                   # fallback GPT-4o
GEMINI_API_KEY=...                   # fallback Gemini
EMBEDDING_MODEL=text-embedding-3-small
LLM_TIMEOUT_SECONDS=45

# === DOCUMENT PARSING ===
LLAMA_PARSE_API_KEY=...
DOCUMENT_PARSE_BACKEND=llamaparse    # llamaparse | unstructured

# === EMAIL ===
EMAIL_BACKEND=smtp                   # smtp | dummy
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=...
SMTP_TLS=true

# === NOTIFICATIONS ===
SCHEDULER_ENABLED=true
SCHEDULER_DEADLINE_CHECK_CRON="0 8 * * *"   # ogni giorno alle 08:00

# === AUTH ===
AUTH_BACKEND=local                   # local | clerk
CLERK_SECRET_KEY=...                 # solo se AUTH_BACKEND=clerk
CLERK_PUBLISHABLE_KEY=...

# === OBSERVABILITY ===
LANGSMITH_API_KEY=...                # opzionale, solo se tracing abilitato
LANGSMITH_ENABLED=false
LOG_LEVEL=INFO
```

---

_Fine documento — v2.1_