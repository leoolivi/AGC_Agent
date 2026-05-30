# Implementation Plan: Admin & Compliance Guardian MVP (`acg-mvp
## Overview

Piano di implementazione in 4 fasi (10 settimane) per l'ACG MVP. L'ordine segue il blueprint §19:
prima Protocol + dummy adapter (i test devono girare con dummy prima di LangGraph), poi LangGraph
con sequenza lineare prima dei conditional edges, poi RiskEngine hardcoded prima di YAML, poi
HITL state machine prima dell'UI.

Stack: Python 3.12 · FastAPI · LangGraph · SQLAlchemy async · PostgreSQL 16 + pgvector ·
React 19 · TypeScript · shadcn/ui · Hypothesis (property tests).

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 0,
      "tasks": ["0", "0.1", "0.3", "0.4", "0.5", "0.6", "0.8"]
    },
    {
      "wave": 1,
      "tasks": ["0.2", "0.7", "0.9", "1"]
    },
    {
      "wave": 2,
      "tasks": ["2.1", "2.2"]
    },
    {
      "wave": 3,
      "tasks": ["2.3", "3.1", "4.1"]
    },
    {
      "wave": 4,
      "tasks": ["3.2", "3.3"]
    },
    {
      "wave": 5,
      "tasks": ["3.4", "4.2", "6.1"]
    },
    {
      "wave": 6,
      "tasks": ["4.3", "6.2", "5.1"]
    },
    {
      "wave": 7,
      "tasks": ["5.2", "5.3"]
    },
    {
      "wave": 8,
      "tasks": ["5.4", "7.1", "8.1"]
    },
    {
      "wave": 9,
      "tasks": ["7.2", "8.2", "8.3"]
    },
    {
      "wave": 10,
      "tasks": ["8.4", "9"]
    },
    {
      "wave": 11,
      "tasks": ["10.1", "11.1", "12.1", "13.1", "14.1", "15.1", "16.1", "17.1"]
    },
    {
      "wave": 12,
      "tasks": ["10.2", "10.3", "10.4", "10.5", "10.6", "10.7", "11.2", "12.2", "12.3", "13.2", "14.2", "16.2", "17.2", "18.1"]
    },
    {
      "wave": 13,
      "tasks": ["10.8", "11.3", "11.4", "12.4", "13.3", "13.4", "14.3", "14.4", "15.2", "16.3", "16.4", "17.3", "17.4", "18.2"]
    },
    {
      "wave": 14,
      "tasks": ["11.5", "18.3", "19"]
    },
    {
      "wave": 15,
      "tasks": ["20.1", "21.1", "22.1", "23.1", "24.1", "24.2", "24.3", "25.1"]
    },
    {
      "wave": 16,
      "tasks": ["20.2", "21.2", "22.2", "23.2", "25.2"]
    },
    {
      "wave": 17,
      "tasks": ["20.3", "21.2", "22.3", "25.3"]
    },
    {
      "wave": 18,
      "tasks": ["26"]
    }
  ]
}
```
  0 (struttura progetto)
  └── 0.1 (Protocol/Port + dummy)
      └── 0.2* (test Protocol dummy)
  └── 0.3 (schema DB + migration)
  └── 0.4 (domain models Pydantic)
  └── 0.5 (Docker Compose + env)
  └── 0.6 (auth JWT)
      └── 0.7* (test auth)
  └── 0.8 (rules.yaml + RiskEngine)
      └── 0.9* (PBT risk score monotonicity)
  └── 1 (Checkpoint Phase 0)

Phase 1 (Document Core)
  2 (storage + upload)
  └── 2.1 (storage adapters)
  └── 2.2 (endpoint upload/documenti)
      └── 2.3* (test integrazione upload)
  └── 3 (parsing pipeline)
      └── 3.1 (parser adapters)
          └── 3.2* (PBT parser round-trip)
      └── 3.3 (DocumentPipeline asincrona)
          └── 3.4* (test integrazione pipeline)
  └── 4 (classificazione + estrazione)
      └── 4.1 (LLM adapters + FallbackChain)
      └── 4.2 (classificazione + estrazione campi)
          └── 4.3* (test classificazione)
  └── 5 (confidence gate + HITL)
      └── 5.1 (ConfidenceGate + PendingConfirmation)
          └── 5.2* (PBT confidence gate completeness)
      └── 5.3 (endpoint HITL + state machine)
          └── 5.4* (PBT HITL invariant)
  └── 6 (VectorStore + chunking)
      └── 6.1 (pgvector adapter)
          └── 6.2* (test chunking + VectorStore)
  └── 7 (TriageGraph DOCUMENT_UPLOADED)
      └── 7.1 (TriageGraph)
          └── 7.2* (test TriageGraph)
  └── 8 (Inbox API + AuditService)
      └── 8.1 (AuditService + endpoint audit)
          └── 8.2* (PBT audit log append-only)
      └── 8.3 (Agent Inbox API)
          └── 8.4* (PBT inbox urgency ordering)
  └── 9 (Checkpoint Phase 1)

Phase 2 (Intelligence + Inbox)
  10 (frontend Phase 1)
  └── 10.1 (scaffolding frontend)
  └── 10.2 (typed API client)
  └── 10.3 (DashboardPage)
  └── 10.4 (InboxCard)
  └── 10.5 (DocumentUploadZone + DocumentsPage)
  └── 10.6 (ReviewCard)
  └── 10.7 (ConfirmationCard + ConfirmationsPage)
      └── 10.8* (test componenti frontend)
  └── 11 (TriageGraph completo + WorkflowGraph)
      └── 11.1 (TriageGraph tutti gli event types)
      └── 11.2 (WorkflowGraph)
          └── 11.3* (PBT workflow template completeness)
      └── 11.4 (3 workflow template Phase 2)
          └── 11.5* (test WorkflowGraph + template)
  └── 12 (Deadline Engine)
      └── 12.1 (DeadlineService + endpoint)
      └── 12.2 (estrazione deadline da documenti)
      └── 12.3 (DeadlineScheduler APScheduler)
          └── 12.4* (test DeadlineService)
  └── 13 (Notification System)
      └── 13.1 (NotificationService + adapter)
      └── 13.2 (endpoint notifiche)
      └── 13.3 (polling frontend)
          └── 13.4* (test NotificationService)
  └── 14 (Email Drafting)
      └── 14.1 (SMTP adapter + EmailDraftService)
      └── 14.2 (endpoint email drafts)
      └── 14.3 (EmailDraftPreview frontend)
          └── 14.4* (test EmailDraftService)
  └── 15 (Guardrails Layer)
      └── 15.1 (GuardrailLayer tutti i livelli)
          └── 15.2* (test GuardrailLayer)
  └── 16 (Chat Agent)
      └── 16.1 (ChatAgentGraph + intent mapping)
      └── 16.2 (endpoint chat + sessioni)
      └── 16.3 (AgentChatInterface frontend)
          └── 16.4* (test ChatAgent)
  └── 17 (DailyDigestService + Scheduler)
      └── 17.1 (DailyDigestService)
      └── 17.2 (APScheduler)
      └── 17.3 (digest email HTML)
          └── 17.4* (test DailyDigestService)
  └── 18 (Settings + Dashboard Overview)
      └── 18.1 (endpoint settings + dashboard)
      └── 18.2 (SettingsPage frontend)
          └── 18.3* (test settings + health)
  └── 19 (Checkpoint Phase 2)

Phase 3 (Polish & Production)
  20 (Trust Progressivo)
  └── 20.1 (aggiornamento user_extraction_trust)
  └── 20.2 (effective_threshold() RiskEngine)
      └── 20.3* (test trust progressivo)
  └── 21 (Workflow Template Phase 3)
      └── 21.1 (3 template aggiuntivi)
          └── 21.2* (test template Phase 3)
  └── 22 (detect_patterns() + Digest Email HTML)
      └── 22.1 (detect_patterns() con LLM)
      └── 22.2 (digest email HTML)
          └── 22.3* (test detect_patterns)
  └── 23 (LangSmith + Osservabilità)
      └── 23.1 (LangSmith tracing)
      └── 23.2 (logging strutturato + health check)
  └── 24 (Frontend Phase 3)
      └── 24.1 (AuditPage)
      └── 24.2 (DeadlinesPage + DocumentDetailPage)
      └── 24.3 (Google Calendar stub)
  └── 25 (Docker Compose production + Security)
      └── 25.1 (docker-compose.cloud.yml)
      └── 25.2 (security review)
          └── 25.3* (test suite finale)
  └── 26 (Checkpoint Phase 3)
```

Tasks marcati con `*` sono test (unit, integration, o property-based). I task `*` sono opzionali nel senso che non bloccano il task successivo se falliscono per motivi ambientali, ma devono passare prima del checkpoint di fase.

---

## Notes

- Seguire l'ordine di implementazione del blueprint §19: Protocol + dummy adapter prima di LangGraph; LangGraph con sequenza lineare prima dei conditional edges; RiskEngine hardcoded prima di YAML; HITL state machine prima dell'UI.
- Nessun `import` di adapter in `app/core/` — violazione bloccante.
- Nessun global state nell'agent — tutto passa attraverso `AgentState` TypedDict.
- Nessun prompt hardcodato nel codice Python — sempre file `.md` in `app/agent/prompts/`.
- `mypy --strict` deve passare su tutto il backend prima di ogni checkpoint.
- I task `[DEFERRED]` (multi-tenancy, n8n, ML risk scoring, Google Calendar reale, RBAC, billing, file encryption) hanno interfaccia reale ma implementazione stub con commento `[TODO: TD-XXX]`.
- Le funzionalità `[FORBIDDEN_MVP]` (invio a enti pubblici, pagamenti, modifica gestionali, consigli fiscali interpretativi) devono essere rifiutate attivamente a runtime dal GuardrailLayer — non implementate né lasciate come stub.

---

## Tasks

### Phase 0 — Foundation (Settimana 1)

- [ ] 0. Struttura progetto e configurazione ambiente
  - Creare la struttura directory completa: `backend/app/{core,agent,adapters,api,db}`, `frontend/src`, `infra/`
  - Inizializzare `pyproject.toml` con dipendenze pinned: FastAPI, SQLAlchemy async, Alembic, LangGraph, Pydantic v2, structlog, pytest, Hypothesis
  - Inizializzare `package.json` frontend con React 19, TypeScript, Vite, shadcn/ui, TailwindCSS, React Query, Zustand
  - _Requirements: 2.1, 2.2, 21.4_

  - [ ] 0.1 Definire tutti i Protocol/Port con implementazioni dummy
    - Creare `app/core/ports/storage.py` → `FileStoragePort` + `FileMetadata`
    - Creare `app/core/ports/llm.py` → `LLMProviderPort` + `LLMResponse`
    - Creare `app/core/ports/parser.py` → `DocumentParserPort` + `ParsedDocument`
    - Creare `app/core/ports/email.py` → `EmailSenderPort` + `EmailMessage`
    - Creare `app/core/ports/vector.py` → `VectorStorePort` + `VectorSearchResult`
    - Creare `app/core/ports/calendar.py` → `CalendarPort` + `CalendarEvent` (stub TD-002)
    - Creare `app/core/ports/notifier.py` → `NotifierPort`
    - Creare `app/adapters/dummy/` con implementazione dummy per ogni Protocol (testabile in isolamento)
    - _Requirements: 2.7, 21.1, 21.3, 26.9_

  - [~] 0.2 Scrivere test unitari per ogni Protocol dummy
    - Verificare che ogni dummy implementi correttamente l'interfaccia Protocol
    - Verificare che ogni dummy sia istanziabile e chiamabile senza dipendenze esterne
    - _Requirements: 21.3, 28.5_


  - [~] 0.3 Creare schema DB completo con migration Alembic iniziale
    - Creare `app/db/models.py` con tutti i modelli SQLAlchemy: `users`, `documents`, `document_chunks`, `deadlines`, `agent_tasks`, `pending_confirmations`, `email_drafts`, `notifications`, `audit_log`, `agent_inbox`, `user_extraction_trust`
    - Aggiungere commenti `-- [TODO: multi-tenancy]` su ogni tabella (TD-001)
    - Creare indici: `ivfflat` su `document_chunks.embedding`, `agent_inbox(user_id, status, urgency, created_at DESC)`, `pending_confirmations(group_id)`
    - Creare migration Alembic iniziale `0001_initial_schema.py`
    - _Requirements: 2.5, 2.6, 10.8, 17.7, 24.1_

  - [~] 0.4 Creare modelli di dominio Pydantic v2
    - Creare `app/core/domain/`: `Document`, `Deadline`, `AgentTask`, `PendingConfirmation`, `EmailDraft`, `Notification`, `AuditEntry`, `AgentInboxItem`, `AgentEvent`, `UserExtractionTrust`
    - Creare `app/agent/state.py` → `AgentState` TypedDict
    - Creare `app/agent/workflows/registry.py` → `WorkflowTemplate`, `WorkflowStep`, `WorkflowTemplateRegistry` (stub, 0 template)
    - _Requirements: 21.5, 11.7_

  - [~] 0.5 Configurare Docker Compose e variabili d'ambiente
    - Creare `docker-compose.yml` con servizi: PostgreSQL 16, MinIO, backend FastAPI (:8000), frontend React (:3000)
    - Aggiungere health check su ogni servizio (timeout 30s)
    - Creare `infra/env.example` con tutte le variabili documentate inline (senza segreti reali)
    - Configurare auto-apply migration Alembic all'avvio con `ENVIRONMENT=development`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_


  - [~] 0.6 Implementare autenticazione JWT locale
    - Creare `app/core/services/auth_service.py` con hash bcrypt (cost factor ≥ 12), validazione password ≥ 8 caratteri
    - Creare `app/api/v1/auth.py` → `POST /auth/login` (risposta JWT firmata, scadenza configurabile)
    - Creare middleware JWT in `app/api/deps.py` con risposta HTTP 401 per token scaduto/non valido
    - Implementare isolamento utente: HTTP 403 per accesso a risorse di altri utenti
    - Supportare `AUTH_BACKEND=clerk` come alternativa configurabile
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [~] 0.7 Scrivere test unitari per autenticazione
    - Test JWT valido/scaduto/non valido → HTTP 401 con motivo corretto
    - Test credenziali errate → HTTP 401 generico (no user enumeration)
    - Test accesso risorsa altro utente → HTTP 403
    - _Requirements: 1.2, 1.4, 1.5, 28.8_

  - [~] 0.8 Creare `rules.yaml` e `RiskEngine` hardcoded
    - Creare `app/agent/risk/rules.yaml` con `tool_risk_base`, `context_modifiers`, soglie confidence (`field_extraction: 0.85`, `deadline_extraction: 0.90`, `amount_extraction: 0.92`, `document_classification: 0.80`)
    - Creare `app/agent/risk/engine.py` → `RiskEngine.compute_risk()`, `get_threshold()`, `effective_threshold()` (Phase 0-2: ignora `user_extraction_trust`)
    - Validare caricamento `rules.yaml` all'avvio: exit code non-zero se assente o malformato
    - _Requirements: 7.1, 7.2, 7.7, 7.8, 7.9_

  - [~] 0.9 Scrivere property test per Risk Score Monotonicity
    - **Property 1: Risk Score Monotonicity**
    - Per qualsiasi `tool_name` valido e qualsiasi sottoinsieme di modificatori di contesto, `compute_risk()` deve restituire un valore in `[risk_base, 5]`; aggiungere modificatori non può abbassare il risk score
    - Usare `@given(st.sampled_from(valid_tools), st.lists(st.sampled_from(context_modifiers)))`
    - **Validates: Requirements 7.2, 7.7**

- [~] 1. Checkpoint Phase 0 — Ensure all tests pass, ask the user if questions arise.


---

### Phase 1 — Document Core (Settimane 2-4)

- [ ] 2. Storage layer e upload documenti

  - [~] 2.1 Implementare adapter storage (Local, MinIO, S3)
    - Creare `app/adapters/storage/local_adapter.py` → `LocalStorageAdapter` implementa `FileStoragePort`
    - Creare `app/adapters/storage/minio_adapter.py` → `MinIOAdapter` con boto3
    - Creare `app/adapters/storage/s3_adapter.py` → `S3Adapter` con boto3
    - Implementare `build_storage_key(user_id, file_id, filename)` centralizzato con formato `{user_id}/{year}/{month}/{file_id}_{original_filename}`
    - Selezione adapter da `FILE_STORAGE_BACKEND` in `app/api/deps.py`
    - Auto-creazione `LOCAL_STORAGE_PATH` se non esiste
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 2.8_

  - [~] 2.2 Implementare endpoint upload e gestione documenti
    - Creare `app/api/v1/documents.py` con: `POST /documents/upload` (max 20MB, validazione Content-Type), `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/download`, `DELETE /documents/{id}` (→ PendingConfirmation risk_level=4, HTTP 202), `POST /documents/search`
    - Upload: salva su storage → crea record `parse_status=pending` → avvia pipeline in background
    - HTTP 503 se storage fallisce (nessun record DB creato)
    - HTTP 415 per Content-Type non supportato
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [~] 2.3 Scrivere test integrazione per upload documenti
    - Test upload valido → record DB creato, file su storage
    - Test HTTP 415 per Content-Type non supportato
    - Test HTTP 503 se storage non disponibile
    - Test DELETE → PendingConfirmation creata, HTTP 202
    - _Requirements: 3.1, 3.2, 3.3, 3.7, 28.8_


- [ ] 3. Pipeline di parsing documenti

  - [~] 3.1 Implementare adapter parser (LlamaParse, Unstructured, pandas)
    - Creare `app/adapters/parsers/llamaparse_adapter.py` → implementa `DocumentParserPort` per PDF
    - Creare `app/adapters/parsers/unstructured_adapter.py` → implementa `DocumentParserPort` per PDF fallback + XLS/XLSX
    - Creare `app/adapters/parsers/pandas_adapter.py` → implementa `DocumentParserPort` per CSV e XLS/XLSX fallback
    - Creare `app/adapters/parsers/parser_with_fallback.py` → `ParserWithFallback`: tenta primary, se `confidence < 0.60` tenta fallback, restituisce max(confidence)
    - Creare `ParserRegistry` con selezione tramite `can_parse()` senza logica hardcodata nei service
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 25.1, 25.3, 25.4_

  - [~] 3.2 Scrivere property test per Parser Round-Trip
    - **Property 5: Parser Round-Trip**
    - Per qualsiasi `ParsedDocument` valido, serializzare in JSON e deserializzare deve produrre un oggetto con campi chiave identici (`text`, `tables`, `metadata`, `confidence`)
    - Usare `@given(st.builds(ParsedDocument, text=st.text(min_size=1), confidence=st.floats(0.0, 1.0)))`
    - **Validates: Requirements 25.5**

  - [~] 3.3 Implementare DocumentPipeline asincrona
    - Creare `app/core/services/document_pipeline.py` con sequenza: parse → classify → extract_fields → confidence_gate → chunk_and_embed → trigger_triage
    - Esecuzione asincrona in background dopo upload (non blocca HTTP response)
    - Aggiornare `parse_status`: `parsed` se successo, `failed` se tutti i parser falliscono
    - Notifica `level=warning` + log audit se parsing fallisce
    - _Requirements: 4.5, 4.6, 4.7, 4.8_

  - [~] 3.4 Scrivere test integrazione per DocumentPipeline
    - Test con file reali: PDF strutturato, PDF scansionato, XLSX, CSV
    - Test fallback parser: LlamaParse confidence < 0.60 → Unstructured
    - Test `parse_status=failed` + notifica se tutti i parser falliscono
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 28.4_


- [ ] 4. Classificazione documento ed estrazione campi

  - [~] 4.1 Implementare adapter LLM (Anthropic, OpenAI, Gemini) e FallbackChain
    - Creare `app/adapters/llm/anthropic_adapter.py`, `openai_adapter.py`, `gemini_adapter.py` → implementano `LLMProviderPort`
    - Creare `app/adapters/llm/fallback_chain.py` → `FallbackChain`: PRIMARY → FALLBACK_1 → FALLBACK_2
    - Trigger fallback: 5xx, timeout (45s), 429, connection refused
    - Log ogni fallback con provider tentato e motivo in AuditLog (`action_type=llm_fallback`)
    - Creare prompt di classificazione ed estrazione come file `.md` in `app/agent/prompts/`
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 16.7_

  - [~] 4.2 Implementare classificazione documento e estrazione campi per tipo
    - Classificare documento in: `fattura`, `contratto`, `nota_spese`, `altro` con confidence
    - Estrarre campi specifici per tipo (fattura: 10 campi; contratto: 9 campi; nota_spese: 5 campi; altro: 5 campi)
    - Associare `confidence_score` (0.0–1.0) a ogni campo estratto
    - Salvare tutto in `extracted_metadata` (JSONB) con confidence per campo
    - Salvare campo come `null` con `confidence_score=0.0` se non presente
    - Se LLM fallisce → `parse_status=failed`, notifica `level=warning`, log audit
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.10, 5.11_

  - [~] 4.3 Scrivere test unitari per classificazione ed estrazione
    - Test classificazione con mock LLM per ogni tipo documento
    - Test estrazione campi con confidence alta e bassa
    - Test campo non presente → `null` con `confidence_score=0.0`
    - Test fallback LLM → `parse_status=failed`
    - _Requirements: 5.1, 5.10, 5.11, 28.1_


- [ ] 5. Confidence Gate e Review Card aggregata

  - [~] 5.1 Implementare Confidence Gate e creazione PendingConfirmation aggregate
    - Creare `app/core/services/confidence_gate.py`: confronta confidence di ogni campo con soglia da `rules.yaml`
    - Se `document_type_confidence < 0.80` → PendingConfirmation per tipo documento prima di estrarre campi
    - Per ogni campo sotto soglia: creare `PendingConfirmation` con stesso `group_id` UUID e `group_type=document_review`
    - Se tutti i campi ≥ soglia → salva direttamente in `extracted_metadata` senza PendingConfirmation
    - Garantire query `group_id` < 100ms per gruppi fino a 20 campi
    - _Requirements: 5.9, 6.1, 6.2, 6.6, 6.7_

  - [~] 5.2 Scrivere property test per Confidence Gate Completeness
    - **Property 2: Confidence Gate Completeness**
    - Per qualsiasi lista di campi con confidence score, il numero di `PendingConfirmation` create deve essere esattamente uguale al numero di campi con `confidence < soglia`; nessun campo sotto-soglia può essere salvato senza PendingConfirmation
    - Usare `@given(st.lists(st.floats(0.0, 1.0), min_size=1, max_size=20))`
    - **Validates: Requirements 5.9, 6.1, 6.2**

  - [~] 5.3 Implementare endpoint HITL e gestione ciclo vita PendingConfirmation
    - Creare `app/api/v1/confirmations.py`: `GET /confirmations`, `POST /confirmations/{id}/approve`, `POST /confirmations/{id}/reject`
    - Implementare state machine `agent_tasks`: `pending → in_progress → done|failed|skipped` (risk ≤ 2) e `pending → waiting_confirmation → approved → done|rejected` (risk ≥ 3)
    - Approve: aggiorna conferma, esegue tool, aggiorna task `skipped` dipendenti a `pending`, notifica utente
    - Reject: aggiorna conferma, marca task come `rejected`, salva `user_comment`
    - HTTP 422 se `status != pending`, HTTP 403 se utente non autorizzato
    - Risk_Level 4: doppia PendingConfirmation (approvazione contenuto + approvazione esecuzione)
    - Nessun retry automatico su risk ≥ 4
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7, 8.8, 8.9_

  - [~] 5.4 Scrivere property test per HITL Invariant
    - **Property 3: HITL Invariant**
    - Per qualsiasi azione con `risk_score >= 3`, il tool non deve mai essere eseguito senza una `PendingConfirmation` con `status=approved`; proprietà valida indipendentemente dall'ordine di arrivo delle approvazioni
    - Usare `@given(st.integers(min_value=3, max_value=5))` per risk score
    - **Validates: Requirements 7.4, 7.5, 8.1, 8.9**


- [ ] 6. VectorStore, chunking e ricerca semantica

  - [~] 6.1 Implementare pgvector adapter e chunking
    - Creare `app/adapters/vector/pgvector_adapter.py` → implementa `VectorStorePort`
    - Chunking: dimensione massima 512 token, minima 64 token, overlap 64 token
    - Embedding con `text-embedding-3-small` (OpenAI), dimensione vettoriale 1536
    - `VectorStorePort` gestisce internamente la generazione embedding (non esposta al chiamante)
    - `upsert`: salva chunk + embedding in `document_chunks`; se fallisce → log audit, `parse_status=failed`
    - `search`: ricerca coseno filtrata per `user_id`, max 10 risultati default
    - _Requirements: 4.8, 17.5, 17.6, 17.7_

  - [~] 6.2 Scrivere test unitari per chunking e VectorStore
    - Test invarianti chunking: ogni chunk tra 64 e 512 token, overlap corretto
    - Test `search` filtrata per `user_id` (nessun risultato di altri utenti)
    - _Requirements: 4.8, 17.6_

- [ ] 7. TriageGraph per DOCUMENT_UPLOADED

  - [~] 7.1 Implementare TriageGraph (sequenza lineare, solo DOCUMENT_UPLOADED)
    - Creare `app/agent/graphs/triage_graph.py` con nodi in sequenza: `load_context → analyze_event → generate_options → classify_urgency → write_inbox_item`
    - `load_context`: carica max 10 documenti correlati, scadenze active, storico AgentInboxItem ultimi 90 giorni
    - `analyze_event`: LLM analizza evento + contesto
    - `generate_options`: LLM genera 2-3 azioni suggerite (MAX 3 totali, sempre inclusa "Nessuna azione / Archivia")
    - `classify_urgency`: regole hard-coded (immediate/today) + LLM per this_week/low; fallback deterministico `this_week` se LLM fallisce
    - `write_inbox_item`: scrive `AgentInboxItem` su DB; se fallisce → log audit, termina senza notifica
    - Risk score massimo 1 (solo lettura + scrittura interna), mai PendingConfirmation
    - Avvio automatico entro 5s dal completamento DocumentPipeline
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [~] 7.2 Scrivere test unitari per TriageGraph
    - Test sequenza nodi corretta
    - Test urgency rules: immediate (deadline < 24h, pagamento scaduto > 30gg), today (< 7gg)
    - Test max 3 azioni suggerite, sempre inclusa "Nessuna azione / Archivia"
    - Test fallback deterministico `this_week` se LLM fallisce
    - Test risk score massimo 1
    - _Requirements: 9.2, 9.3, 9.4, 9.5_


- [ ] 8. Agent Inbox API e AuditService

  - [~] 8.1 Implementare AuditService e endpoint audit log
    - Creare `app/core/services/audit_service.py` → `AuditService.log()`: INSERT-only su `audit_log`, mai UPDATE/DELETE
    - Creare `app/api/v1/audit.py` → `GET /audit-log` con paginazione e filtri per `action_type` e intervallo date
    - Non loggare valori di segreti, solo riassunti
    - _Requirements: 19.1, 19.2, 19.3, 19.6_

  - [~] 8.2 Scrivere property test per Audit Log Append-Only
    - **Property 4: Audit Log Append-Only**
    - Per qualsiasi sequenza di operazioni sul sistema, il conteggio totale dei record in `audit_log` deve essere monotonicamente non-decrescente; nessuna operazione può ridurre il numero di record
    - Usare `@given(st.lists(st.builds(AuditEntry), min_size=1, max_size=50))`
    - **Validates: Requirements 19.2**

  - [~] 8.3 Implementare Agent Inbox API
    - Creare `app/api/v1/inbox.py`: `GET /inbox` (filtri status/urgency, ordinati per urgency rank poi `created_at DESC`), `GET /inbox/unread-count`, `POST /inbox/{id}/act`, `POST /inbox/{id}/dismiss`, `POST /inbox/trigger-triage`
    - `act`: avvia WorkflowGraph, aggiorna `chosen_action_id`, `chosen_at`, `status=acted`; HTTP 422 se action_id non valido, HTTP 403 se utente non autorizzato
    - `dismiss`: aggiorna `status=dismissed`; HTTP 404 se non esiste, HTTP 403 se non autorizzato
    - Job periodico (ogni ora): aggiorna `status=expired` per item con `expires_at` nel passato
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.9_

  - [~] 8.4 Scrivere property test per Inbox Urgency Ordering
    - **Property 6: Inbox Urgency Ordering**
    - Per qualsiasi insieme di `AgentInboxItem` con urgency mista, `GET /inbox` deve restituire item con `urgency_rank(i) <= urgency_rank(j)` per ogni coppia adiacente; a parità di urgency, `created_at DESC`
    - Usare `@given(st.lists(st.builds(AgentInboxItem, urgency=st.sampled_from(["immediate","today","this_week","low"])), min_size=2, max_size=50))`
    - **Validates: Requirements 10.1**

- [~] 9. Checkpoint Phase 1 — Ensure all tests pass, ask the user if questions arise.


---

### Phase 2 — Intelligence + Inbox (Settimane 5-7)

- [ ] 10. Frontend Phase 1 — Dashboard inbox-first e componenti base

  - [~] 10.1 Scaffolding frontend React 19 + routing
    - Inizializzare Vite + React 19 + TypeScript + TailwindCSS + shadcn/ui
    - Configurare React Query (server state) + Zustand (UI state)
    - Creare routing con React Router: `/`, `/documents`, `/documents/:id`, `/deadlines`, `/agent`, `/confirmations`, `/email-drafts`, `/audit`, `/settings`
    - Creare layout base: sidebar sinistra con navigazione, header con ricerca globale + campanella notifiche + profilo
    - _Requirements: 22.1, 22.2, 22.5, 22.6_

  - [~] 10.2 Implementare typed API client
    - Generare client TypeScript tipizzato da OpenAPI schema del backend
    - Configurare interceptor per JWT header `Authorization: Bearer <token>`
    - Configurare gestione errori globale (401 → redirect login, 403 → toast errore)
    - _Requirements: 22.1_

  - [~] 10.3 Implementare DashboardPage inbox-first
    - Layout a due colonne: Agent Inbox (colonna principale) + widget Scadenze (colonna laterale)
    - Widget `DeadlineSemaphore`: tre colonne rosso/giallo/verde con count, click → naviga a `/deadlines` filtrata
    - Chat input in basso (placeholder per Phase 2)
    - _Requirements: 10.7, 22.3, 22.4_

  - [~] 10.4 Implementare componente `InboxCard`
    - Bordo sinistro colorato per urgency: rosso=immediate, arancio=today, grigio=this_week/low
    - Analisi agente compatta (max 160 caratteri visibili, espandibile al click)
    - Bottoni con verb specifici da `suggested_actions[].label`
    - Click su azione ad alto risk (≥ 3): apre preview/bozza, non esegue direttamente
    - Click su "Dismiss": chiama `POST /inbox/{id}/dismiss`
    - _Requirements: 10.5, 10.6_

  - [~] 10.5 Implementare `DocumentUploadZone` e `DocumentsPage`
    - Drag-and-drop con validazione formati (PDF, XLSX, XLS, CSV) e dimensione max 20MB
    - Progress bar durante parsing (polling `GET /documents/{id}` ogni 3s su `parse_status`)
    - Al termine: redirect a `DocumentDetailPage` se `parsed`, messaggio errore inline se `failed`
    - `DocumentsPage`: lista paginata con filtri per `document_type`, `parse_status`, date range
    - _Requirements: 3.9, 22.2_

  - [~] 10.6 Implementare `ReviewCard` aggregata
    - Raggruppa `PendingConfirmation` per `group_id` in un'unica card
    - Campi ✓ (confidence alta): non editabili di default, click per modificare
    - Campi ⚠ (confidence bassa): editabili, focus automatico al primo
    - Campi ✗ (non trovati): vuoti editabili con placeholder "inserisci manualmente"
    - Pulsanti "Conferma" (chiama `POST /confirmations/{id}/approve` per ogni item del gruppo) e "Salta"
    - _Requirements: 6.3, 6.4, 6.5_

  - [~] 10.7 Implementare `ConfirmationCard` e `ConfirmationsPage`
    - Card con descrizione human-readable, dati estratti editabili in-place
    - Pulsanti "Approva" / "Rifiuta" con campo commento opzionale per rifiuto
    - `ConfirmationsPage`: lista di tutte le conferme pendenti
    - _Requirements: 8.6, 22.2_

  - [~] 10.8 Scrivere test componenti frontend
    - Test `InboxCard`: rendering per ogni urgency, click azioni, dismiss
    - Test `ReviewCard`: rendering campi ✓/⚠/✗, submit conferma/salta
    - Test `DocumentUploadZone`: validazione formato, progress, redirect
    - _Requirements: 10.5, 6.3_


- [ ] 11. TriageGraph completo per tutti gli event types

  - [~] 11.1 Estendere TriageGraph per tutti gli event types
    - Aggiungere gestione eventi: `EMAIL_RECEIVED`, `DEADLINE_APPROACHING`, `DEADLINE_OVERDUE`, `USER_CHAT_MESSAGE`, `MANUAL_TRIGGER`
    - Adattare `load_context` per ogni tipo di evento (es. per `DEADLINE_OVERDUE`: carica fatture correlate, storico solleciti)
    - Adattare `generate_options` per suggerire azioni contestuali per tipo evento
    - _Requirements: 9.1, 9.8_

  - [~] 11.2 Implementare WorkflowGraph
    - Creare `app/agent/graphs/workflow_graph.py` con nodi: `load_workflow_template → validate_args → execute_steps → report_result`
    - `validate_args`: chiede all'utente solo i dati mancanti (non re-chiede quelli già presenti)
    - `execute_steps`: applica RiskEngine a ogni step, rispetta soglie HITL
    - `report_result`: aggiorna `AgentInboxItem` come `acted`, notifica utente
    - Avviabile da: scelta utente in inbox, intent chat, automaticamente per risk ≤ 2
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.8_

  - [~] 11.3 Scrivere property test per Workflow Template Completeness
    - **Property 7: Workflow Template Completeness**
    - Per qualsiasi `AgentInboxItem` prodotto dal TriageGraph, ogni `workflow_id` in `suggested_actions` deve corrispondere a un template nel `WorkflowTemplateRegistry`
    - Usare `@given(st.builds(AgentEvent, event_type=st.sampled_from(list(AgentEventType))))`
    - **Validates: Requirements 11.6, 11.7**

  - [~] 11.4 Implementare i 3 workflow template Phase 2
    - `draft_payment_reminder`: `search_documents` (risk 1) → `draft_email` (risk 3)
    - `process_document`: `get_document` (risk 1) → `classify_and_extract` (risk 2) → `create_deadline` (risk 2)
    - `create_deadline_from_document`: `search_documents` (risk 1) → `create_deadline` (risk 2)
    - Registrare tutti e 3 nel `WorkflowTemplateRegistry`
    - _Requirements: 11.6, 11.7_

  - [~] 11.5 Scrivere test unitari per WorkflowGraph e template
    - Test esecuzione completa di ogni template con adapter mock
    - Test `validate_args`: chiede solo dati mancanti
    - Test skip di step bloccati su HITL
    - _Requirements: 11.2, 11.3, 11.4, 28.6_


- [ ] 12. Deadline Engine

  - [~] 12.1 Implementare DeadlineService e endpoint deadlines
    - Creare `app/core/services/deadline_service.py`: `create()`, `get_upcoming()`, `check_and_notify()`
    - Creare `app/api/v1/deadlines.py`: `GET /deadlines`, `POST /deadlines`, `PUT /deadlines/{id}`, `DELETE /deadlines/{id}` (→ PendingConfirmation risk_level=3), `GET /deadlines/upcoming`
    - Supportare ricorrenza: `none`, `monthly`, `quarterly`, `semi_annual`, `annual`, `custom` (cron in `recurrence_config`)
    - _Requirements: 13.4, 13.5, 13.6, 13.7, 13.8, 13.9_

  - [~] 12.2 Implementare estrazione deadline da documenti
    - Integrare estrazione deadline nel DocumentPipeline dopo classificazione
    - Confidence ≥ 0.90 → crea `Deadline` con `source=ai_extracted`, notifica `level=info`
    - Confidence < 0.90 → crea `PendingConfirmation` con dati pre-compilati
    - _Requirements: 13.1, 13.2, 13.3_

  - [~] 12.3 Implementare DeadlineScheduler con APScheduler
    - Configurare APScheduler per eseguire `check_and_notify()` ogni giorno alle 08:00
    - Inviare notifiche preventive per scadenze in `notify_days_before` (default: 30, 7, 3, 1 giorni prima)
    - Applicare soglie `red_days`/`yellow_days` per determinare canale notifica
    - _Requirements: 13.10, 13.11_

  - [~] 12.4 Scrivere test unitari per DeadlineService
    - Test creazione manuale e da AI con confidence alta/bassa
    - Test ricorrenza: calcolo prossima scadenza per ogni tipo
    - Test `check_and_notify`: notifiche inviate per scadenze nei giorni configurati
    - _Requirements: 13.1, 13.2, 13.3, 13.9, 28.1_


- [ ] 13. Sistema di Notifiche

  - [~] 13.1 Implementare NotificationService e adapter notifier
    - Creare `app/core/services/notification_service.py` → `NotificationService.dispatch()`
    - Creare `app/adapters/notifier/inapp_notifier.py` → scrive su tabella `notifications`
    - Creare `app/adapters/notifier/email_notifier.py` → invia via `EmailSenderPort`
    - Selezionare canali in base a `level` + `notification_settings` utente
    - _Requirements: 15.1, 15.5_

  - [~] 13.2 Implementare endpoint notifiche
    - Creare `app/api/v1/notifications.py`: `GET /notifications` (unread first, paginata), `POST /notifications/{id}/read`, `POST /notifications/read-all`
    - Creare notifiche `level=action` per ogni nuova `PendingConfirmation` e `EmailDraft` in `pending_review`
    - Creare notifiche `level=urgent` per scadenze entro `red_days`, `level=warning` entro `yellow_days`
    - _Requirements: 15.2, 15.3, 15.7, 15.8, 15.9_

  - [~] 13.3 Implementare polling notifiche nel frontend
    - Badge campanella nell'header con count notifiche `level=action` non lette
    - Polling `GET /inbox/unread-count` ogni 30 secondi
    - _Requirements: 15.4, 15.6, 10.2_

  - [~] 13.4 Scrivere test unitari per NotificationService
    - Test dispatch per ogni livello con preferenze utente diverse
    - Test canali selezionati correttamente in base a `notification_settings`
    - _Requirements: 15.1, 15.5, 28.1_


- [ ] 14. Email Drafting System

  - [~] 14.1 Implementare SMTP adapter e EmailDraftService
    - Creare `app/adapters/email/smtp_adapter.py` → implementa `EmailSenderPort` con configurazione SMTP
    - Creare `app/core/services/email_draft_service.py`: `create_draft()`, `approve()`, `send()`
    - `approve()`: aggiorna a `status=approved`, crea `PendingConfirmation` risk_level=4 per invio
    - `send()`: HTTP 422 se `status != approved`; invia via `EmailSenderPort`; log audit
    - Template email Jinja2 in `app/templates/email/`: sollecito_pagamento, notifica_scadenza, notifica_documento, conferma_azione
    - _Requirements: 14.1, 14.4, 14.5, 14.6, 14.7, 14.9_

  - [~] 14.2 Implementare endpoint email drafts
    - Creare `app/api/v1/email_drafts.py`: `GET /email-drafts`, `GET /email-drafts/{id}`, `PUT /email-drafts/{id}`, `POST /email-drafts/{id}/approve`, `POST /email-drafts/{id}/send`, `DELETE /email-drafts/{id}`
    - `PUT`: accetta modifiche solo se `status=pending_review`
    - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

  - [~] 14.3 Implementare `EmailDraftPreview` nel frontend
    - Preview HTML dell'email con editor inline per modifiche pre-approvazione
    - Pulsanti "Approva" / "Rifiuta" / "Modifica"
    - `EmailDraftsPage`: lista bozze con filtro per status
    - _Requirements: 14.8, 22.2_

  - [~] 14.4 Scrivere test unitari per EmailDraftService
    - Test ciclo di vita completo: `pending_review → approved → sent`
    - Test HTTP 422 per send su bozza non approved
    - Test doppia conferma per risk_level=4
    - _Requirements: 14.5, 14.6, 14.7, 14.9, 28.1_


- [ ] 15. Guardrails Layer

  - [~] 15.1 Implementare GuardrailLayer (tutti e 3 i livelli)
    - Creare `app/agent/guardrails/guardrail_layer.py` con `check_input()`, `check_action()`, `check_output()`
    - Creare `app/agent/guardrails/constitution.md` con regole assolute (non modificabile dall'utente)
    - Creare `app/agent/guardrails/blacklist.yaml` con azioni vietate MVP (id, description, keywords, error_message)
    - Livello 1 (input): PII detection (CF, P.IVA, IBAN, IBAN), jailbreak detection, blacklist check
    - Livello 2 (execution): verifica blacklist + Constitution su ogni tool call
    - Livello 3 (output): validazione formato (date ISO 8601, importi numerici, P.IVA con checksum), PII re-check
    - Log audit con `action_type=guardrail_block` per ogni blocco
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9_

  - [~] 15.2 Scrivere test unitari per GuardrailLayer
    - Test blocco per ogni voce della blacklist
    - Test blocco output che viola Constitution (consiglio fiscale interpretativo)
    - Test PII detection: CF, P.IVA, IBAN rilevati e gestiti
    - Test validazione formato output: date non ISO 8601, P.IVA non valida
    - _Requirements: 18.2, 18.4, 18.5, 18.6, 18.7, 28.3_


- [ ] 16. Chat Agent

  - [~] 16.1 Implementare ChatAgentGraph con intent mapping
    - Creare `app/agent/graphs/chat_agent.py` con `intent_classifier` che mappa messaggi a `workflow_id` noti
    - Se match trovato: avvia `WorkflowGraph` con argomenti estratti dal messaggio
    - Se no match: pianifica azioni custom con RiskEngine
    - Mantenere stato sessione in `AgentState` TypedDict (no global state)
    - Prompt model-agnostic come file `.md` in `app/agent/prompts/`
    - _Requirements: 16.1, 16.2, 16.3, 16.7, 16.8_

  - [~] 16.2 Implementare endpoint chat e sessioni
    - Creare `app/api/v1/agent.py`: `POST /agent/query`, `GET /agent/sessions/{id}`, `GET /agent/tasks`
    - `POST /agent/query`: accetta `{ message, session_id }`, restituisce risposta + stato azioni
    - `GET /agent/sessions/{id}`: stato sessione con azioni eseguite, pendenti, saltate
    - _Requirements: 16.1, 16.4, 16.5_

  - [~] 16.3 Implementare `AgentChatInterface` nel frontend
    - Chat con messaggi che mostrano stato azioni inline: badge per azioni eseguite, link a conferme create, errori inline
    - Integrazione nella DashboardPage (in basso) e nella `AgentPage` dedicata
    - _Requirements: 16.6, 22.7_

  - [~] 16.4 Scrivere test unitari per ChatAgent
    - Test intent mapping: messaggio → workflow_id corretto
    - Test no match → pianificazione azioni custom
    - Test stato sessione in `AgentState` (no global state)
    - _Requirements: 16.2, 16.3, 16.8_


- [ ] 17. DailyDigestService e Scheduler

  - [~] 17.1 Implementare DailyDigestService
    - Creare `app/services/daily_digest_service.py`: `generate_for_user()`, `generate_for_all_users()`
    - `collect_situation()`: query DB senza LLM (deadline overdue, urgenti, settimana, pending_review, bozze, inbox non risolti >48h)
    - `detect_patterns()`: Phase 2 → template strutturato (no LLM); Phase 3 → LLM leggero max 200 token
    - `compose_digest()`: template Jinja2 con sezioni fisse (Attenzione immediata, Da fare questa settimana, Tutto il resto, Suggerimento del giorno)
    - Scrive `AgentInboxItem` con `event_type=daily_digest`, `urgency=immediate`, `expires_at=mezzanotte`
    - Errore su un utente non blocca gli altri
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.7, 12.8_

  - [~] 17.2 Configurare APScheduler per digest e deadline check
    - Configurare APScheduler in `app/main.py` con due job:
      - `DailyDigestService.generate_for_all_users()` alle 08:00 ogni giorno
      - `DeadlineService.check_and_notify()` alle 08:00 ogni giorno
    - Abilitare/disabilitare scheduler tramite `SCHEDULER_ENABLED` env var
    - _Requirements: 12.1, 13.10_

  - [~] 17.3 Implementare invio digest email opzionale
    - Se utente ha abilitato digest email in settings: invia versione HTML via SMTP con template Jinja2 dedicato
    - _Requirements: 12.6_

  - [~] 17.4 Scrivere test unitari per DailyDigestService
    - Test `collect_situation()`: dati corretti per ogni categoria (overdue, urgenti, ecc.)
    - Test `compose_digest()`: struttura sezioni fisse presente
    - Test errore su un utente non blocca gli altri
    - _Requirements: 12.3, 12.7, 12.8_


- [ ] 18. Settings e Dashboard Overview

  - [~] 18.1 Implementare endpoint settings e dashboard overview
    - Creare `app/api/v1/settings.py`: `GET /settings`, `PUT /settings`
    - Creare `app/api/v1/dashboard.py`: `GET /dashboard/overview` (contatori semaforo, conferme pendenti, bozze in attesa, attività recente)
    - Creare `app/api/v1/health.py`: `GET /health` con check DB + storage
    - _Requirements: 23.1, 23.2, 23.7, 27.4_

  - [~] 18.2 Implementare `SettingsPage` nel frontend
    - Configurazione soglie alert: `red_days`, `yellow_days`, `notify_days_before`
    - Configurazione canali notifica per livello
    - Configurazione SMTP
    - Toggle digest email giornaliero
    - _Requirements: 22.8, 23.3, 23.4, 23.5_

  - [~] 18.3 Scrivere test integrazione per endpoint settings e health
    - Test `GET /settings` → preferenze utente corrette
    - Test `PUT /settings` → aggiornamento persistito
    - Test `GET /health` → `ok` con tutti i servizi up, `degraded` con storage down
    - _Requirements: 23.1, 23.2, 27.4, 28.8_

- [~] 19. Checkpoint Phase 2 — Ensure all tests pass, ask the user if questions arise.


---

### Phase 3 — Polish & Production (Settimane 8-10)

- [ ] 20. Trust Progressivo

  - [~] 20.1 Implementare aggiornamento `user_extraction_trust` da ReviewCard
    - Aggiornare `user_extraction_trust` ad ogni interazione con ReviewCard:
      - Conferma senza modificare → `confirmed_without_edit += 1`, `total_extractions += 1`
      - Modifica valore → `edited_extractions += 1`, `total_extractions += 1`
    - Usare `INSERT ... ON CONFLICT DO UPDATE` per upsert atomico
    - _Requirements: 24.2, 24.3, 24.6_

  - [~] 20.2 Attivare `effective_threshold()` nel RiskEngine
    - Implementare `RiskEngine.effective_threshold(user_id, document_type, field_name) -> float`
    - Abbassare la soglia base in proporzione all'`accuracy` storica dell'utente per quel campo
    - Sostituire `get_threshold()` con `effective_threshold()` nel Confidence Gate
    - _Requirements: 24.4, 24.5_

  - [~] 20.3 Scrivere test unitari per Trust Progressivo
    - Test `effective_threshold()`: soglia si abbassa con accuracy alta, rimane base con accuracy bassa
    - Test upsert atomico: nessuna race condition su aggiornamenti concorrenti
    - _Requirements: 24.4, 24.5_


- [ ] 21. Workflow Template Phase 3

  - [~] 21.1 Implementare workflow template aggiuntivi
    - `reply_to_email`: `search_documents` (risk 1) → `draft_email` (risk 3) con contesto email originale
    - `generate_payment_status_report`: `list_deadlines` (risk 1) → `search_documents` (risk 1) → `draft_summary` (risk 2)
    - `batch_send_reminders`: `list_deadlines` (risk 1) → `draft_email` × N (risk 3) → batch review
    - Registrare tutti e 3 nel `WorkflowTemplateRegistry`
    - _Requirements: 11.6_

  - [~] 21.2 Scrivere test per workflow template Phase 3
    - Test esecuzione completa di ogni template con adapter mock
    - Test `batch_send_reminders`: N bozze create, una sola Review Card aggregata
    - _Requirements: 11.6, 28.6_


- [ ] 22. detect_patterns() con LLM e Digest Email HTML

  - [~] 22.1 Attivare `detect_patterns()` con LLM nel DailyDigest
    - Sostituire template strutturato con chiamata LLM leggero (max 200 token output)
    - Identificare pattern anomali (es. cliente che non paga da 60 giorni)
    - Generare al massimo 1 suggerimento proattivo per digest
    - _Requirements: 12.4_

  - [~] 22.2 Implementare digest email HTML
    - Creare template Jinja2 HTML per digest email in `app/templates/email/daily_digest.html`
    - Inviare via SMTP se utente ha abilitato digest email
    - _Requirements: 12.6_

  - [~] 22.3 Scrivere test per detect_patterns()
    - Test con mock LLM: suggerimento generato correttamente
    - Test max 1 suggerimento per digest
    - _Requirements: 12.4_


- [ ] 23. LangSmith Tracing e Osservabilità

  - [~] 23.1 Integrare LangSmith tracing
    - Configurare LangSmith in `app/main.py` se `LANGSMITH_ENABLED=true`
    - Inviare tracce LangGraph a LangSmith usando `LANGSMITH_API_KEY`
    - _Requirements: 27.3_

  - [~] 23.2 Completare logging strutturato e health check
    - Verificare che tutti i service usino `structlog` con formato JSON strutturato
    - Verificare che nessun segreto sia loggato (API key, password, token JWT)
    - Completare `GET /health` con check DB + storage + risposta `{ status, checks }`
    - _Requirements: 27.1, 27.2, 27.4, 27.5, 27.6_


- [ ] 24. Audit Page e Frontend Phase 3

  - [~] 24.1 Implementare `AuditPage` nel frontend
    - Lista del log in sola lettura con filtri per tipo azione e data
    - Paginazione
    - _Requirements: 19.7, 22.2_

  - [~] 24.2 Completare `DeadlinesPage` e `DocumentDetailPage`
    - `DeadlinesPage`: calendario + lista, filtri per status/type/date, crea manuale
    - `DocumentDetailPage`: metadati estratti, scadenze correlate, link audit
    - _Requirements: 22.2_

  - [~] 24.3 Implementare Google Calendar adapter stub
    - Creare `app/adapters/calendar/google_calendar_adapter.py` come stub che implementa `CalendarPort`
    - Stub: log dell'operazione, restituisce un `event_id` fittizio
    - Commento `[TODO: TD-002]` con istruzioni per implementazione reale
    - _Requirements: 21.9, 26.5_


- [ ] 25. Docker Compose production-ready e Security Review

  - [~] 25.1 Creare `docker-compose.cloud.yml` production-ready
    - Configurare per cloud: punta a Supabase/Neon (DB), S3 (storage)
    - Aggiungere variabili d'ambiente per `AUTH_BACKEND=clerk`
    - Configurare restart policy e resource limits
    - _Requirements: 2.1_

  - [~] 25.2 Security review e hardening
    - Verificare che nessun segreto sia esposto nei log o nelle risposte API
    - Verificare isolamento utente su tutti gli endpoint (HTTP 403 per risorse di altri utenti)
    - Verificare che `mypy --strict` passi su tutto il backend
    - Verificare che nessun `import` di adapter sia presente in `app/core/`
    - _Requirements: 1.5, 21.1, 21.8_

  - [~] 25.3 Test suite finale con dataset realistico
    - Eseguire test di integrazione con file PDF/XLSX/CSV reali
    - Verificare pipeline completa: upload → parsing → triage → inbox → azione → audit
    - Verificare DailyDigest: generazione corretta per utente con dati realistici
    - _Requirements: 28.4_

- [~] 26. Checkpoint Phase 3 — Ensure all tests pass, ask the user if questions arise.
