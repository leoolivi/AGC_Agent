# Requirements Document

## Introduction

L'**Admin & Compliance Guardian (ACG)** è un assistente amministrativo AI per PMI italiane. Il sistema monitora, analizza e propone azioni su documenti, scadenze e comunicazioni aziendali, delegando sempre la responsabilità finale all'utente umano per ogni azione con effetti esterni.

Il paradigma UX primario è l'**Agent Inbox**: l'agente non aspetta domande, ma analizza proattivamente gli eventi (upload documenti, scadenze in arrivo, email ricevute) e presenta all'utente situazioni già analizzate con opzioni d'azione pre-compilate. La chat è una feature avanzata, non il punto di ingresso principale.

**Regola d'oro: Reliability > Autonomy.** Il sistema fa il massimo lavoro possibile in autonomia, ma richiede sempre approvazione umana esplicita per ogni azione che può causare danni o effetti esterni.

---

## Glossary

- **ACG**: Admin & Compliance Guardian — il sistema descritto in questo documento.
- **Agent**: il componente AI basato su LangGraph che analizza eventi, pianifica azioni e le esegue entro i limiti di rischio consentiti.
- **Agent_Inbox**: la coda di situazioni analizzate dall'agente, presentate all'utente come card azionabili.
- **AgentInboxItem**: singolo elemento dell'Agent_Inbox, prodotto dal TriageGraph dopo l'analisi di un evento.
- **TriageGraph**: grafo LangGraph leggero che processa ogni evento in arrivo e produce un AgentInboxItem senza eseguire azioni rischiose.
- **WorkflowGraph**: grafo LangGraph che esegue una sequenza di azioni specifiche, avviato da una scelta dell'utente nell'inbox o dalla chat.
- **DailyDigestGraph**: grafo LangGraph che gira ogni mattina alle 08:00 e produce il briefing giornaliero.
- **WorkflowTemplate**: definizione dichiarativa di un workflow riutilizzabile (sequenza di step, argomenti richiesti, risk score per step).
- **WorkflowTemplateRegistry**: registro centralizzato di tutti i WorkflowTemplate disponibili.
- **RiskEngine**: componente che calcola il risk score di ogni azione pianificata leggendo `rules.yaml`.
- **Risk_Level**: intero da 0 a 5 che classifica il rischio di un'azione (0=READ, 1=INTERNAL_WRITE, 2=EXTRACT_AND_CREATE, 3=DRAFT, 4=EXTERNAL_ACTION, 5=FORBIDDEN).
- **HITL**: Human-In-The-Loop — meccanismo di approvazione esplicita da parte dell'utente per azioni a rischio elevato.
- **PendingConfirmation**: record DB che rappresenta una richiesta di approvazione in attesa di risposta dall'utente.
- **ReviewCard**: interfaccia aggregata che mostra tutti i campi estratti da un documento in un'unica card di revisione, raggruppati per `group_id`.
- **Confidence_Gate**: controllo che blocca l'esecuzione autonoma di un'estrazione AI quando la confidence è sotto soglia, richiedendo conferma umana.
- **Confidence_Score**: valore float 0.0–1.0 che rappresenta la certezza dell'AI sull'accuratezza di un dato estratto.
- **Deadline**: scadenza amministrativa (pagamento, rinnovo contratto, adempimento fiscale, ecc.) tracciata dal sistema.
- **EmailDraft**: bozza di email generata dall'agente, in attesa di revisione e approvazione prima dell'invio.
- **AuditLog**: registro append-only di tutte le azioni eseguite dal sistema, non modificabile.
- **DailyDigest**: briefing giornaliero generato automaticamente alle 08:00 con la situazione del giorno.
- **DocumentPipeline**: sequenza di operazioni (parsing, classificazione, estrazione campi, confidence gate) eseguita su ogni documento caricato.
- **Parser**: componente che estrae testo strutturato da un file (PDF, XLSX, XLS, CSV).
- **LlamaParse**: parser primario per PDF strutturati.
- **Unstructured**: parser di fallback per PDF (scansioni) e parser primario per XLS/XLSX.
- **Constitution**: file markdown con le regole assolute e non negoziabili dell'agente.
- **Blacklist**: file YAML con le azioni vietate nell'MVP, rifiutate a runtime.
- **Guardrail_Layer**: sistema a tre livelli (input, execution, output) che applica le regole di sicurezza.
- **Trust_Progressivo**: meccanismo (Phase 3) che abbassa le soglie di confidence per campi che l'utente ha storicamente confermato senza modifiche.
- **APScheduler**: libreria Python per la pianificazione di task periodici (es. digest giornaliero, check scadenze).
- **pgvector**: estensione PostgreSQL per la ricerca vettoriale semantica sui chunk dei documenti.
- **JWT**: JSON Web Token — meccanismo di autenticazione usato dall'API.
- **PMI**: Piccola e Media Impresa — target utente del sistema.
- **SMTP**: Simple Mail Transfer Protocol — protocollo usato per l'invio di email.

---

## Requirements

---

### Requisito 1: Autenticazione e Gestione Utente

**User Story:** Come utente di una PMI italiana, voglio accedere al sistema con credenziali sicure, così da proteggere i dati aziendali riservati.

#### Acceptance Criteria

1. THE ACG SHALL esporre un endpoint `POST /auth/login` che accetta email e password e restituisce un JWT firmato con scadenza configurabile tramite variabile d'ambiente (default: 24 ore; range valido: 1 minuto–30 giorni).
2. WHEN un JWT scaduto o non valido è presentato in una richiesta, THE ACG SHALL rispondere con HTTP 401 con un corpo JSON che indica il motivo del rifiuto (es. `"token_expired"`, `"token_invalid"`) senza esporre dettagli interni dell'implementazione.
3. THE ACG SHALL proteggere tutti gli endpoint `/api/v1/*` richiedendo un JWT valido nell'header `Authorization: Bearer <token>`.
4. IF una richiesta di login viene effettuata con credenziali non valide (email non esistente o password errata), THEN THE ACG SHALL rispondere con HTTP 401 con un messaggio generico che non distingue tra email non trovata e password errata, per prevenire user enumeration.
5. IF un utente tenta di accedere a risorse di un altro utente (tramite `user_id` nel path o nel body della richiesta), THEN THE ACG SHALL rispondere con HTTP 403 senza esporre dati dell'altro utente.
6. WHERE `AUTH_BACKEND=local`, THE ACG SHALL gestire autenticazione con hash bcrypt delle password (cost factor ≥ 12) senza dipendenze da servizi esterni, e SHALL richiedere una password di almeno 8 caratteri alla registrazione.
7. WHERE `AUTH_BACKEND=clerk`, THE ACG SHALL delegare l'autenticazione a Clerk usando `CLERK_SECRET_KEY` e `CLERK_PUBLISHABLE_KEY`.

---

### Requisito 2: Infrastruttura e Setup Progetto

**User Story:** Come sviluppatore, voglio un ambiente di sviluppo riproducibile con un singolo comando, così da poter iniziare a lavorare senza configurazioni manuali complesse.

#### Acceptance Criteria

1. THE ACG SHALL fornire un `docker-compose.yml` che avvia i servizi: PostgreSQL, MinIO, backend FastAPI, frontend React, con health check su ogni servizio che verifica la disponibilità entro 30 secondi dall'avvio.
2. THE ACG SHALL fornire un file `infra/env.example` con tutte le variabili d'ambiente documentate inline, senza valori segreti reali.
3. WHEN il backend FastAPI viene avviato con `ENVIRONMENT=development`, THE ACG SHALL applicare automaticamente le migration Alembic pendenti; IF una migration fallisce, THEN il backend SHALL terminare con exit code non-zero e loggare il dettaglio dell'errore prima di accettare richieste.
4. THE ACG SHALL esporre il backend su porta 8000 e il frontend su porta 3000 nella configurazione Docker Compose di sviluppo.
5. THE ACG SHALL creare tutte le tabelle del database definite nel blueprint (users, documents, document_chunks, deadlines, agent_tasks, pending_confirmations, email_drafts, notifications, audit_log, agent_inbox, user_extraction_trust) nella migration iniziale di Phase 0.
6. THE ACG SHALL includere commenti `-- [TODO: multi-tenancy]` su ogni tabella del database per segnalare il debito tecnico `TD-001`.
7. THE ACG SHALL definire tutti i Protocol/Port (`FileStoragePort`, `LLMProviderPort`, `DocumentParserPort`, `EmailSenderPort`, `VectorStorePort`, `CalendarPort`, `NotifierPort`) con implementazioni dummy funzionanti prima di qualsiasi codice applicativo; ogni dummy SHALL essere testabile in isolamento senza dipendenze esterne.
8. WHEN `FILE_STORAGE_BACKEND=local`, THE ACG SHALL creare automaticamente la directory `LOCAL_STORAGE_PATH` se non esiste, senza richiedere configurazione aggiuntiva.

---

### Requisito 3: Upload e Gestione Documenti

**User Story:** Come titolare di PMI, voglio caricare documenti aziendali (fatture, contratti, note spese) nel sistema, così da avere un archivio centralizzato e permettere all'agente di analizzarli.

#### Acceptance Criteria

1. THE ACG SHALL accettare upload di file nei formati: `application/pdf` (`.pdf`), `application/vnd.ms-excel` (`.xls`), `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (`.xlsx`), `text/csv` (`.csv`), con dimensione massima di 20 MB per file.
2. IF un file viene caricato con un Content-Type non supportato, THEN THE ACG SHALL rispondere con HTTP 415 e un messaggio che elenca i formati accettati.
3. WHEN un documento viene caricato con successo, THE ACG SHALL salvare il file nello storage configurato con path `{user_id}/{year}/{month}/{file_id}_{original_filename}` e creare un record nella tabella `documents` con `parse_status=pending`; IF il salvataggio nello storage fallisce, THEN THE ACG SHALL rispondere con HTTP 503 senza creare il record nel database.
4. THE ACG SHALL esporre `GET /documents` con paginazione (default: 20 elementi per pagina, massimo: 100) e filtri per `document_type`, `parse_status`, e intervallo di date `created_at`.
5. THE ACG SHALL esporre `GET /documents/{id}` che restituisce il record documento con i metadati estratti in `extracted_metadata`.
6. THE ACG SHALL esporre `GET /documents/{id}/download` che restituisce il file originale dallo storage.
7. WHEN `DELETE /documents/{id}` è chiamato, THE ACG SHALL creare una `PendingConfirmation` con `risk_level=4` invece di eliminare immediatamente il documento, e rispondere con HTTP 202 e l'ID della conferma.
8. THE ACG SHALL esporre `POST /documents/search` che esegue ricerca semantica sui chunk vettoriali filtrata per `user_id`, accettando `{ query: string, filters: object }` e restituendo al massimo 10 risultati per default.
9. THE ACG SHALL esporre un componente frontend `DocumentUploadZone` con drag-and-drop che accetta i formati supportati, mostra il progresso del parsing, e al termine: reindirizza a `DocumentDetailPage` se il parsing ha avuto successo, oppure mostra un messaggio di errore inline se il parsing è fallito.

---

### Requisito 4: Pipeline di Parsing Documenti

**User Story:** Come utente, voglio che il sistema estragga automaticamente il testo e le tabelle dai documenti caricati, così da non dover inserire manualmente i dati.

#### Acceptance Criteria

1. WHEN un documento PDF viene caricato, THE DocumentPipeline SHALL tentare il parsing con LlamaParse come parser primario.
2. IF LlamaParse restituisce un `ParsedDocument` con `confidence < 0.60`, THEN THE DocumentPipeline SHALL tentare il parsing con Unstructured come fallback e usare il risultato con confidence più alta tra i due.
3. WHEN un file XLS o XLSX viene caricato, THE DocumentPipeline SHALL usare Unstructured come parser primario; IF Unstructured restituisce `confidence < 0.60`, THEN THE DocumentPipeline SHALL tentare pandas come fallback e usare il risultato con confidence più alta.
4. WHEN un file CSV viene caricato, THE DocumentPipeline SHALL usare pandas per il parsing diretto senza chiamate AI.
5. WHEN il parsing di un documento ha successo, THE DocumentPipeline SHALL aggiornare `parse_status` a `parsed`.
6. IF il parsing fallisce su tutti i parser disponibili per un documento, THEN THE DocumentPipeline SHALL aggiornare `parse_status=failed`, creare una notifica `level=warning` per l'utente, e registrare l'errore nell'AuditLog.
7. THE DocumentPipeline SHALL eseguire il parsing in modo asincrono dopo l'upload, senza bloccare la risposta HTTP all'utente.
8. WHEN un documento viene parsato con successo, THE DocumentPipeline SHALL suddividere il testo in chunk (dimensione massima: 512 token, minima: 64 token, overlap: 64 token) e salvare gli embedding nella tabella `document_chunks` tramite `VectorStorePort`; IF `VectorStorePort.upsert` fallisce, THEN THE DocumentPipeline SHALL registrare l'errore nell'AuditLog e impostare `parse_status=failed`.
9. IF un file viene caricato con un formato non supportato (non PDF, XLS, XLSX, CSV), THEN THE DocumentPipeline SHALL rispondere con HTTP 415 con un messaggio che elenca i formati accettati.

---

### Requisito 5: Classificazione Documento ed Estrazione Campi

**User Story:** Come utente, voglio che il sistema identifichi automaticamente il tipo di documento e ne estragga i campi rilevanti, così da non dover inserire manualmente dati come importi, date e parti contraenti.

#### Acceptance Criteria

1. WHEN un documento è stato parsato, THE DocumentPipeline SHALL classificarlo in una delle categorie: `fattura`, `contratto`, `nota_spese`, `altro`, salvando il tipo in `document_type` e la confidence in `document_type_confidence`.
2. IF `document_type_confidence < 0.80` (soglia `document_classification` in `rules.yaml`), THEN THE DocumentPipeline SHALL creare una `PendingConfirmation` per la conferma del tipo documento prima di procedere all'estrazione campi.
3. WHEN il tipo documento è `fattura`, THE DocumentPipeline SHALL estrarre i campi: `numero_fattura`, `data_emissione`, `data_scadenza`, `importo_lordo`, `importo_iva`, `importo_netto`, `fornitore_nome`, `fornitore_piva`, `cliente_nome`, `cliente_piva`.
4. WHEN il tipo documento è `contratto`, THE DocumentPipeline SHALL estrarre i campi: `tipo_contratto`, `data_firma`, `data_inizio`, `data_scadenza`, `data_rinnovo_tacito`, `parti`, `oggetto`, `importo_annuale`, `clausole_recesso`.
5. WHEN il tipo documento è `nota_spese`, THE DocumentPipeline SHALL estrarre i campi: `data`, `dipendente`, `voci` (lista con descrizione, importo, categoria), `totale`, `stato_rimborso`.
6. WHEN il tipo documento è `altro`, THE DocumentPipeline SHALL estrarre i campi: `titolo`, `data_documento`, `tipo_stimato`, `parti_coinvolte`, `date_rilevanti`.
7. THE DocumentPipeline SHALL associare un `confidence_score` (float 0.0–1.0) a ogni campo estratto, riflettendo la certezza dell'AI sull'accuratezza del valore estratto.
8. THE DocumentPipeline SHALL salvare tutti i campi estratti con le relative confidence in `extracted_metadata` (JSONB) del record documento.
9. WHEN la DocumentPipeline estrae campi da un documento, THE Confidence_Gate SHALL confrontare la confidence di ogni campo con la soglia configurata in `rules.yaml` per quel tipo di campo (`field_extraction`: 0.85, `amount_extraction`: 0.92); IF la confidence di un campo è inferiore alla soglia applicabile, THEN THE DocumentPipeline SHALL includere quel campo nella ReviewCard aggregata del documento (vedi Requisito 6).
10. IF un campo non è presente nel documento o non è estraibile, THEN THE DocumentPipeline SHALL salvare il campo come `null` con `confidence_score = 0.0` in `extracted_metadata`.
11. IF la chiamata LLM per la classificazione o l'estrazione fallisce (errore di rete, timeout, tutti i provider esauriti), THEN THE DocumentPipeline SHALL impostare `parse_status=failed`, creare una notifica `level=warning` per l'utente, e registrare il dettaglio del fallimento nell'AuditLog.

---

### Requisito 6: Confidence Gate e Review Card Aggregata

**User Story:** Come utente, voglio rivedere in un'unica schermata tutti i campi estratti da un documento che richiedono verifica, così da poter confermare o correggere i dati in modo efficiente senza gestire N richieste separate.

#### Acceptance Criteria

1. WHEN la DocumentPipeline estrae campi da un documento, THE Confidence_Gate SHALL confrontare la confidence di ogni campo con la soglia configurata in `rules.yaml` per quel tipo di campo (`field_extraction`: 0.85, `deadline_extraction`: 0.90, `amount_extraction`: 0.92).
2. WHEN uno o più campi hanno `confidence < soglia`, THE DocumentPipeline SHALL creare una `PendingConfirmation` per ogni campo sotto soglia, assegnando lo stesso `group_id` UUID a tutte le conferme dello stesso documento e impostando `group_type=document_review`.
3. WHEN il frontend riceve una `PendingConfirmation` con `group_type=document_review`, THE ACG SHALL renderizzare una `ReviewCard` aggregata che mostra tutti i campi dello stesso `group_id` in un'unica card, differenziando visivamente: campi con confidence alta (✓, non editabili di default), campi con confidence bassa (⚠, editabili con focus automatico), campi non trovati (✗, vuoti editabili).
4. WHEN l'utente clicca "Conferma" nella ReviewCard, THE ACG SHALL salvare tutti i valori (modificati o confermati) in `extracted_metadata`, aggiornare tutte le `PendingConfirmation` del gruppo a `status=approved`, aggiornare `user_extraction_trust` per ogni campo interagito, e avanzare il workflow.
5. WHEN l'utente clicca "Salta" nella ReviewCard, THE ACG SHALL aggiornare tutte le `PendingConfirmation` del gruppo a `status=rejected` senza salvare i dati estratti; i campi con confidence alta già presenti in `extracted_metadata` SHALL essere preservati.
6. IF tutti i campi di un documento hanno `confidence >= soglia`, THEN THE DocumentPipeline SHALL procedere senza creare `PendingConfirmation`, salvando i dati estratti direttamente in `extracted_metadata`.
7. THE ACG SHALL garantire che le query per recuperare tutte le `PendingConfirmation` di un `group_id` completino in meno di 100ms per gruppi fino a 20 campi.

---

### Requisito 7: Sistema di Rischio e Classificazione Azioni

**User Story:** Come utente, voglio che il sistema esegua autonomamente solo le azioni sicure e mi chieda conferma per quelle rischiose, così da mantenere il controllo senza dover approvare ogni singola operazione di lettura.

#### Acceptance Criteria

1. THE RiskEngine SHALL calcolare il risk score di ogni azione pianificata leggendo la configurazione da `app/agent/risk/rules.yaml`, caricato all'avvio del backend.
2. THE RiskEngine SHALL applicare il risk score base da `tool_risk_base` in `rules.yaml` e aggiungere i modificatori di contesto da `context_modifiers` (es. +1 se l'azione coinvolge una parte esterna, +1 se coinvolge un importo monetario); il risk score finale SHALL essere limitato a un massimo di 5.
3. IF il risk score calcolato è `<= 2`, THEN THE Agent SHALL eseguire l'azione autonomamente e registrare un log strutturato nell'AuditLog.
4. IF il risk score calcolato è `3`, THEN THE Agent SHALL creare una `PendingConfirmation` con i dati pre-compilati, notificare l'utente con `level=action`, e attendere approvazione esplicita prima di eseguire.
5. IF il risk score calcolato è `>= 4`, THEN THE Agent SHALL richiedere approvazione esplicita tramite UI dedicata, anche se l'utente ha già espresso consenso in chat nella stessa sessione.
6. IF il risk score calcolato è `5` o l'azione è nella Blacklist, THEN THE Agent SHALL rifiutare l'azione, rispondere con una spiegazione del motivo, e registrare il rifiuto nell'AuditLog con `status=rejected`.
7. THE RiskEngine SHALL esporre un metodo `compute_risk(action: PlannedAction, context: dict) -> int` con implementazione basata su `rules.yaml` nell'MVP, sostituibile con un modello ML senza modificare l'interfaccia (`[TODO: TD-003]`).
8. IF `rules.yaml` è assente o malformato all'avvio del backend, THEN THE ACG SHALL terminare con exit code non-zero e loggare il dettaglio dell'errore, senza avviare il server.
9. THE ACG SHALL supportare la modifica di `rules.yaml` senza richiedere il redeploy del backend; il ricaricamento avviene all'avvio del processo; il hot-reload in produzione è opzionale e configurabile tramite variabile d'ambiente.

---

### Requisito 8: HITL Queue — Gestione Conferme

**User Story:** Come utente, voglio poter approvare o rifiutare le azioni proposte dall'agente da un'unica interfaccia, così da mantenere il controllo su tutte le operazioni rischiose senza dover cercare le richieste in luoghi diversi.

#### Acceptance Criteria

1. THE ACG SHALL gestire il ciclo di vita di ogni `agent_task` attraverso gli stati: `pending → in_progress → done | failed | skipped` per azioni con risk ≤ 2, e `pending → waiting_confirmation → approved → done | rejected` per azioni con risk ≥ 3.
2. WHEN l'agente incontra un task in stato `waiting_confirmation` durante l'esecuzione di un workflow, THE Agent SHALL saltare quel task e marcare come `skipped` tutti i task che hanno `depends_on_task_id` puntante al task bloccato.
3. THE ACG SHALL esporre `GET /confirmations` che restituisce la lista delle `PendingConfirmation` con `status=pending` per l'utente autenticato.
4. WHEN `POST /confirmations/{id}/approve` è chiamato, THE ACG SHALL aggiornare la conferma a `status=approved`, eseguire il tool associato, aggiornare i task `skipped` dipendenti a `pending`, e notificare l'utente al termine; IF l'esecuzione del tool fallisce dopo l'approvazione, THEN THE ACG SHALL aggiornare il task a `status=failed`, registrare l'errore nell'AuditLog, e notificare l'utente con `level=warning`.
5. WHEN `POST /confirmations/{id}/reject` è chiamato con un commento opzionale, THE ACG SHALL aggiornare la conferma a `status=rejected`, marcare il task associato come `rejected`, e registrare il commento in `user_comment`.
6. THE ACG SHALL esporre un componente frontend `ConfirmationCard` che mostra la descrizione human-readable, i dati estratti editabili in-place, e i pulsanti "Approva" / "Rifiuta".
7. IF un'azione di Risk_Level 4 viene approvata tramite `PendingConfirmation`, THEN THE ACG SHALL creare una seconda `PendingConfirmation` separata con `risk_level=4` per l'esecuzione effettiva, prima di procedere.
8. IF `POST /confirmations/{id}/approve` o `POST /confirmations/{id}/reject` è chiamato su una conferma con `status != pending` o appartenente a un altro utente, THEN THE ACG SHALL rispondere con HTTP 422 (stato non valido) o HTTP 403 (utente non autorizzato) rispettivamente.
9. THE ACG SHALL non eseguire retry automatici su azioni di Risk_Level ≥ 4: solo l'utente può ri-approvare tramite una nuova `PendingConfirmation`.

---

### Requisito 9: TriageGraph — Analisi Proattiva degli Eventi

**User Story:** Come utente, voglio che il sistema analizzi automaticamente ogni evento rilevante (upload documento, scadenza in arrivo, email ricevuta) e mi presenti la situazione già analizzata con opzioni d'azione, così da non dover interpretare i dati grezzi da solo.

#### Acceptance Criteria

1. THE TriageGraph SHALL processare eventi dei tipi: `DOCUMENT_UPLOADED`, `EMAIL_RECEIVED`, `DEADLINE_APPROACHING`, `DEADLINE_OVERDUE`, `USER_CHAT_MESSAGE`, `MANUAL_TRIGGER`.
2. WHEN il TriageGraph processa un evento, THE TriageGraph SHALL eseguire i nodi in sequenza: `load_context → analyze_event → generate_options → classify_urgency → write_inbox_item`.
3. THE TriageGraph SHALL generare al massimo 3 azioni suggerite per ogni AgentInboxItem, includendo sempre l'opzione "Nessuna azione / Archivia" come una delle azioni suggerite.
4. THE TriageGraph SHALL classificare l'urgency dell'AgentInboxItem usando le seguenti regole in ordine di priorità: `immediate` se la deadline ha `due_date` entro 24 ore dalla data corrente oppure se un pagamento risulta scaduto da più di 30 giorni rispetto alla data corrente; `today` se la deadline ha `due_date` entro 7 giorni dalla data corrente; per tutti gli altri casi, il nodo `classify_urgency` SHALL invocare l'LLM per determinare `this_week` o `low`; IF la chiamata LLM fallisce durante la classificazione `this_week`/`low`, THEN THE TriageGraph SHALL assegnare il valore `this_week` come fallback deterministico.
5. THE TriageGraph SHALL operare con risk score massimo 1 (solo lettura + scrittura interna), senza mai creare `PendingConfirmation` o bloccarsi su conferme.
6. WHEN il nodo `write_inbox_item` persiste con successo un `AgentInboxItem` nella tabella `agent_inbox`, THE TriageGraph SHALL inviare una notifica in-app all'utente con livello `urgent` se urgency è `immediate`, `warning` se urgency è `today`, e `info` se urgency è `this_week` o `low`; IF la scrittura su `agent_inbox` fallisce, THEN THE TriageGraph SHALL registrare l'errore nel log di audit e terminare senza inviare la notifica.
7. WHEN la DocumentPipeline completa con successo l'elaborazione di un documento, THE TriageGraph SHALL essere avviato automaticamente con evento `DOCUMENT_UPLOADED` entro 5 secondi dal completamento della DocumentPipeline, con `source_ref_id` impostato all'`id` del documento elaborato.
8. THE TriageGraph SHALL includere nel nodo `load_context` al massimo 10 documenti correlati alla stessa entità (fornitore o cliente) del documento sorgente, le scadenze con `status = active`, e lo storico delle `AgentInboxItem` relative alla stessa entità degli ultimi 90 giorni.

---

### Requisito 10: Agent Inbox — Paradigma UX Primario

**User Story:** Come utente, voglio vedere in un'unica dashboard le situazioni già analizzate dall'agente con le opzioni d'azione pre-compilate, così da poter gestire l'amministrazione aziendale in pochi click senza dover cercare informazioni sparse.

#### Acceptance Criteria

1. THE ACG SHALL esporre `GET /inbox` che restituisce la lista degli `AgentInboxItem` dell'utente autenticato, con filtri per `status` e `urgency`, ordinati per urgency (immediate → today → this_week → low) e poi per `created_at DESC`.
2. THE ACG SHALL esporre `GET /inbox/unread-count` che restituisce il conteggio degli item con `status=pending` per il badge nell'header.
3. WHEN `POST /inbox/{id}/act` è chiamato con `{ action_id }`, THE ACG SHALL avviare il WorkflowGraph corrispondente con gli argomenti pre-compilati dell'azione scelta, aggiornare `chosen_action_id` e `chosen_at`, e aggiornare `status=acted`; IF `action_id` non corrisponde a nessuna azione dell'item o l'item non appartiene all'utente autenticato, THEN THE ACG SHALL rispondere con HTTP 422 o HTTP 403 rispettivamente.
4. WHEN `POST /inbox/{id}/dismiss` è chiamato, THE ACG SHALL aggiornare `status=dismissed` senza eseguire alcuna azione; IF l'item non esiste o non appartiene all'utente autenticato, THEN THE ACG SHALL rispondere con HTTP 404 o HTTP 403 rispettivamente.
5. THE ACG SHALL esporre un componente frontend `InboxCard` con: bordo sinistro colorato per urgency (rosso=immediate, arancio=today, grigio=this_week/low), analisi dell'agente compatta (massimo 160 caratteri visibili, espandibile al click), bottoni con verb specifici (non "Esegui" ma "Invia sollecito", "Prepara disdetta", ecc.).
6. WHEN l'utente clicca un bottone di azione ad alto risk (≥ 3) in una InboxCard, THE ACG SHALL aprire una preview/bozza invece di eseguire direttamente.
7. THE ACG SHALL strutturare il dashboard con layout inbox-first: Agent Inbox nella colonna principale, widget Scadenze nella colonna laterale, chat in basso.
8. THE ACG SHALL creare un indice su `agent_inbox(user_id, status, urgency, created_at DESC)` per ottimizzare le query della dashboard.
9. THE ACG SHALL eseguire un job periodico (ogni ora) che aggiorna a `status=expired` tutti gli `AgentInboxItem` con `expires_at` nel passato e `status=pending`; gli item con `status=expired` SHALL essere esclusi dalle query di default di `GET /inbox`.

---

### Requisito 11: WorkflowGraph ed Esecuzione Azioni

**User Story:** Come utente, voglio che il sistema esegua azioni complesse in più step (es. trovare una fattura, generare un sollecito, attendere la mia approvazione) in modo coordinato, così da non dover orchestrare manualmente ogni operazione.

#### Acceptance Criteria

1. THE WorkflowGraph SHALL essere avviato con `workflow_id`, `pre_filled_args`, e `user_id`, e caricare la definizione del workflow dal WorkflowTemplateRegistry.
2. THE WorkflowGraph SHALL eseguire i nodi in sequenza: `load_workflow_template → validate_args → execute_steps → report_result`.
3. WHEN `validate_args` rileva argomenti mancanti, THE WorkflowGraph SHALL richiedere all'utente solo i dati mancanti, senza re-chiedere quelli già presenti.
4. THE WorkflowGraph SHALL eseguire gli step del workflow in sequenza, applicando il RiskEngine a ogni step e rispettando le soglie di approvazione.
5. WHEN il WorkflowGraph completa l'esecuzione, THE WorkflowGraph SHALL aggiornare l'AgentInboxItem di origine come `acted` e inviare una notifica in-app all'utente.
6. THE WorkflowTemplateRegistry SHALL contenere i seguenti template nell'MVP: `draft_payment_reminder`, `process_document`, `create_deadline_from_document` (Phase 2), più `reply_to_email`, `generate_payment_status_report`, `batch_send_reminders` (Phase 3).
7. THE WorkflowTemplateRegistry SHALL essere strutturato in modo che l'aggiunta di un nuovo workflow richieda solo l'aggiunta di un file in `app/agent/workflows/templates/` senza modifiche al core.
8. THE WorkflowGraph SHALL essere avviabile sia da una scelta dell'utente nell'Agent_Inbox, sia da un intent riconosciuto nella chat, sia automaticamente per azioni con risk ≤ 2.

---

### Requisito 12: Daily Digest e Scheduler Proattivo

**User Story:** Come titolare di PMI, voglio ricevere ogni mattina un briefing automatico con la situazione del giorno (scadenze urgenti, documenti in attesa, suggerimenti), così da iniziare la giornata con una visione chiara senza dover aprire manualmente ogni sezione.

#### Acceptance Criteria

1. THE DailyDigestGraph SHALL essere avviato automaticamente ogni giorno alle 08:00 tramite APScheduler per ogni utente attivo.
2. THE DailyDigestGraph SHALL eseguire i nodi in sequenza: `collect_situation → detect_patterns → compose_digest → write_inbox_item → send_email_digest`.
3. WHEN `collect_situation` viene eseguito, THE DailyDigestGraph SHALL raccogliere dal DB (senza LLM): scadenze overdue, scadenze urgenti (entro 7 giorni), scadenze della settimana (7-30 giorni), documenti in pending review, bozze email in attesa, inbox items non risolti da più di 48 ore.
4. WHEN `detect_patterns` viene eseguito (Phase 2: template strutturato; Phase 3: LLM leggero con max 200 token output), THE DailyDigestGraph SHALL identificare pattern anomali (es. cliente che non paga da 60 giorni) e generare al massimo 1 suggerimento proattivo.
5. THE DailyDigestGraph SHALL scrivere un `AgentInboxItem` con `event_type=daily_digest`, `urgency=immediate`, e `expires_at` impostato alla mezzanotte del giorno corrente.
6. WHERE l'utente ha abilitato il digest email nelle impostazioni, THE DailyDigestGraph SHALL inviare la versione HTML del digest tramite SMTP usando un template Jinja2 dedicato.
7. IF la generazione del digest fallisce per un utente, THEN THE DailyDigestGraph SHALL registrare l'errore nel log strutturato e continuare con il prossimo utente senza bloccare l'elaborazione.
8. THE DailyDigestGraph SHALL strutturare il digest con sezioni fisse: "Attenzione immediata" (scadenze overdue + urgenti), "Da fare questa settimana", "Tutto il resto in ordine", "Suggerimento del giorno".
9. THE ACG SHALL esporre `POST /inbox/trigger-triage` per forzare manualmente il triage su un evento (uso dev/debug).

---

### Requisito 13: Deadline Engine

**User Story:** Come utente, voglio che il sistema tracci automaticamente le scadenze estratte dai documenti e mi avvisi con anticipo, così da non perdere mai un pagamento, un rinnovo contrattuale o un adempimento fiscale.

#### Acceptance Criteria

1. WHEN un documento viene processato, THE DocumentPipeline SHALL estrarre le date critiche e creare record `Deadline` per ogni data rilevante identificata dall'LLM, con campi: `title`, `due_date`, `deadline_type` (PAYMENT | CONTRACT_RENEWAL | TAX | LEGAL | CUSTOM), `confidence`, `source_text`.
2. IF la confidence di una deadline estratta è `< 0.90` (soglia `deadline_extraction` in `rules.yaml`), THEN THE DocumentPipeline SHALL creare una `PendingConfirmation` con i dati pre-compilati invece di salvare la deadline direttamente.
3. IF la confidence di una deadline estratta è `>= 0.90`, THEN THE DocumentPipeline SHALL creare la `Deadline` con `source=ai_extracted` e inviare una notifica `level=info` all'utente.
4. THE ACG SHALL esporre `GET /deadlines` con filtri per `status`, `deadline_type`, e intervallo di date `due_date`.
5. THE ACG SHALL esporre `POST /deadlines` per la creazione manuale di scadenze con `source=manual`.
6. THE ACG SHALL esporre `PUT /deadlines/{id}` per la modifica di scadenze esistenti.
7. WHEN `DELETE /deadlines/{id}` è chiamato, THE ACG SHALL creare una `PendingConfirmation` con `risk_level=3` prima di eliminare la scadenza.
8. THE ACG SHALL esporre `GET /deadlines/upcoming` che restituisce le prossime N scadenze per il widget dashboard.
9. THE ACG SHALL supportare le regole di ricorrenza: `none`, `monthly`, `quarterly`, `semi_annual`, `annual`, `custom` (con cron expression in `recurrence_config`).
10. THE DeadlineScheduler SHALL girare ogni giorno alle 08:00 e inviare notifiche preventive per le scadenze che rientrano nei giorni configurati in `notify_days_before` (default: 30, 7, 3, 1 giorni prima).
11. THE ACG SHALL applicare le soglie di alert configurabili dall'utente: `red_days` (default 7), `yellow_days` (default 30), con canali di notifica differenziati per urgenza.

---

### Requisito 14: Sistema di Bozze Email

**User Story:** Come utente, voglio che l'agente generi bozze di email (solleciti, risposte, notifiche) che posso rivedere e modificare prima dell'invio, così da risparmiare tempo nella redazione mantenendo il controllo completo su ogni comunicazione inviata.

#### Acceptance Criteria

1. WHEN il workflow `draft_payment_reminder` o un workflow equivalente viene eseguito, THE Agent SHALL generare una `EmailDraft` tramite LLM con campi: `to_addresses`, `subject`, `body_html`, `body_text`, e salvarla con `status=pending_review`.
2. THE ACG SHALL esporre `GET /email-drafts` che restituisce la lista delle bozze dell'utente con filtro per `status`.
3. THE ACG SHALL esporre `GET /email-drafts/{id}` che restituisce il dettaglio della bozza con preview HTML.
4. THE ACG SHALL esporre `PUT /email-drafts/{id}` per la modifica della bozza, accettando modifiche solo se `status=pending_review`.
5. WHEN `POST /email-drafts/{id}/approve` è chiamato, THE ACG SHALL aggiornare la bozza a `status=approved`, creare una nuova `PendingConfirmation` con `risk_level=4` per l'invio effettivo, e notificare l'utente.
6. WHEN `POST /email-drafts/{id}/send` è chiamato su una bozza con `status=approved`, THE ACG SHALL inviare l'email tramite `EmailSenderPort`, aggiornare `status=sent`, e registrare l'azione nell'AuditLog.
7. IF `POST /email-drafts/{id}/send` è chiamato su una bozza con `status != approved`, THEN THE ACG SHALL rispondere con HTTP 422 e un messaggio che richiede l'approvazione preventiva.
8. THE ACG SHALL esporre un componente frontend `EmailDraftPreview` con preview HTML dell'email e editor inline per modifiche pre-approvazione.
9. THE ACG SHALL gestire il ciclo di vita della bozza attraverso gli stati: `CREATED → PENDING_REVIEW → APPROVED → SENT` con possibilità di `REJECTED` da `PENDING_REVIEW`.

---

### Requisito 15: Sistema di Notifiche

**User Story:** Come utente, voglio ricevere notifiche in-app e via email per gli eventi rilevanti (scadenze in arrivo, conferme pendenti, azioni completate), così da essere sempre aggiornato senza dover controllare manualmente ogni sezione.

#### Acceptance Criteria

1. THE NotificationSystem SHALL supportare quattro livelli di notifica: `info` (azione completata, documento archiviato), `warning` (scadenza in arrivo giallo), `urgent` (scadenza imminente rosso), `action` (richiede azione utente: conferma pendente, bozza in attesa).
2. THE ACG SHALL esporre `GET /notifications` che restituisce le notifiche dell'utente con le non lette prima, con paginazione.
3. THE ACG SHALL esporre `POST /notifications/{id}/read` e `POST /notifications/read-all` per marcare le notifiche come lette.
4. THE ACG SHALL mostrare nel frontend un badge sulla campanella nell'header con il conteggio delle notifiche di livello `action` non lette.
5. THE NotificationDispatcher SHALL selezionare i canali di notifica (in-app, email) in base al livello della notifica e alle preferenze dell'utente configurate in `notification_settings`.
6. WHILE il frontend è aperto, THE ACG SHALL aggiornare il conteggio notifiche tramite polling ogni 30 secondi o tramite WebSocket (scelta implementativa).
7. THE ACG SHALL creare notifiche `level=action` per ogni nuova `PendingConfirmation` e ogni nuova `EmailDraft` in `pending_review`.
8. THE ACG SHALL creare notifiche `level=urgent` per scadenze con `due_date` entro `red_days` giorni.
9. THE ACG SHALL creare notifiche `level=warning` per scadenze con `due_date` entro `yellow_days` giorni.

---

### Requisito 16: Chat Agent

**User Story:** Come utente avanzato, voglio poter interagire con l'agente tramite chat per richiedere analisi, generare documenti o eseguire azioni non presenti nell'inbox, così da avere un canale flessibile per richieste non standard.

#### Acceptance Criteria

1. THE ACG SHALL esporre `POST /agent/query` che accetta `{ message: string, session_id: string }` e restituisce la risposta dell'agente con lo stato delle azioni pianificate.
2. WHEN un messaggio chat viene ricevuto, THE ChatAgent SHALL tentare di mappare l'intent a un `workflow_id` noto tramite `intent_classifier`; se trova un match, SHALL avviare il WorkflowGraph con gli argomenti estratti dal messaggio.
3. IF l'intent non corrisponde a nessun workflow noto, THEN THE ChatAgent SHALL pianificare azioni custom seguendo il meccanismo di execute_loop con risk engine.
4. THE ACG SHALL esporre `GET /agent/sessions/{id}` che restituisce lo stato di una sessione con le azioni eseguite, pendenti e saltate.
5. THE ACG SHALL esporre `GET /agent/tasks` che restituisce i task dell'utente con filtri per `status`.
6. THE ChatAgent SHALL mostrare nel frontend lo stato delle azioni inline nel messaggio: badge per azioni eseguite, link a conferme create, errori inline.
7. THE ChatAgent SHALL usare prompt model-agnostic salvati come file `.md` in `app/agent/prompts/`, senza hardcodare prompt nel codice Python.
8. THE ACG SHALL mantenere lo stato della sessione in `AgentState` senza usare global state, passando tutto attraverso il TypedDict.

---

### Requisito 17: LLM Provider e Fallback Chain

**User Story:** Come operatore del sistema, voglio che il sistema continui a funzionare anche in caso di indisponibilità del provider LLM primario, così da garantire continuità operativa senza intervento manuale.

#### Acceptance Criteria

1. THE ACG SHALL usare Anthropic Claude come provider LLM primario, configurabile tramite `LLM_PRIMARY_PROVIDER` e `ANTHROPIC_API_KEY`.
2. WHEN il provider primario restituisce un errore 5xx, timeout (> `LLM_TIMEOUT_SECONDS`, default 45s), errore 429, o connection refused, THE FallbackChain SHALL tentare automaticamente il provider successivo nella catena: OpenAI GPT-4o → Google Gemini 1.5 Pro.
3. IF tutti i provider nella catena falliscono, THEN THE ACG SHALL restituire un errore all'utente con un messaggio chiaro e registrare ogni fallback con il motivo nell'AuditLog.
4. THE ACG SHALL registrare ogni attivazione del fallback con: provider tentato, motivo del fallback, provider usato effettivamente.
5. THE ACG SHALL usare `text-embedding-3-small` (OpenAI) come modello di embedding di default, configurabile tramite `EMBEDDING_MODEL`.
6. THE VectorStorePort SHALL gestire internamente la generazione degli embedding, accettando testo in input e non esponendo il modello di embedding al chiamante.
7. THE ACG SHALL supportare embedding con dimensione vettoriale 1536 nella tabella `document_chunks` con indice `ivfflat` per ricerca coseno.

---

### Requisito 18: Guardrails e Safety Constitution

**User Story:** Come utente, voglio che il sistema rifiuti automaticamente richieste pericolose o fuori scope (consigli fiscali, invio a enti pubblici, pagamenti), così da non rischiare azioni irreversibili o legalmente problematiche per errore.

#### Acceptance Criteria

1. THE Guardrail_Layer SHALL applicare controlli a tre livelli: input (prima che l'agente veda il messaggio), execution (durante LangGraph), output (prima di restituire al frontend).
2. WHEN un messaggio in input contiene pattern corrispondenti alla Blacklist in `app/agent/guardrails/blacklist.yaml`, THE Guardrail_Layer SHALL rifiutare la richiesta immediatamente con un messaggio esplicativo, senza passarla all'agente.
3. THE Guardrail_Layer SHALL applicare la Constitution come porzione del system prompt dell'agente per ogni chiamata LLM, garantendo che le regole assolute siano sempre attive.
4. IF l'agente genera un output che viola le regole della Constitution (es. consiglio fiscale interpretativo), THEN THE Guardrail_Layer SHALL bloccare l'output, sostituirlo con un messaggio standard, e registrare la violazione nell'AuditLog.
5. THE ACG SHALL rifiutare a runtime qualsiasi azione classificata come `FORBIDDEN_MVP`: invio a enti pubblici (Agenzia Entrate, INPS), esecuzione pagamenti/bonifici, modifica software gestionali, consigli fiscali interpretativi nel caso specifico.
6. THE Guardrail_Layer SHALL eseguire PII detection sull'input: Codice Fiscale, P.IVA, IBAN, coordinate bancarie vengono rilevati e gestiti (redact o flag) prima dell'elaborazione.
7. THE Guardrail_Layer SHALL validare il formato dell'output: date in ISO 8601, importi come valori numerici, P.IVA italiane con checksum valido.
8. THE Constitution SHALL essere un file `app/agent/guardrails/constitution.md` non modificabile dall'utente finale, aggiornabile solo da admin del sistema.
9. THE Blacklist SHALL essere un file `app/agent/guardrails/blacklist.yaml` con voci che includono: `id`, `description`, `keywords`, `error_message`.

---

### Requisito 19: Audit Log

**User Story:** Come titolare di PMI, voglio poter consultare un registro completo e immutabile di tutte le azioni eseguite dal sistema, così da avere tracciabilità completa per audit interni o verifiche di conformità.

#### Acceptance Criteria

1. THE AuditLog SHALL registrare ogni azione eseguita dal sistema con: `user_id`, `session_id`, `action_type`, `tool_name`, `input_summary`, `output_summary`, `risk_score`, `status`, `llm_model`, `created_at`.
2. THE AuditLog SHALL essere append-only: nessun record può essere modificato o eliminato tramite API.
3. THE ACG SHALL esporre `GET /audit-log` con paginazione e filtri per `action_type` e intervallo di date.
4. THE AuditLog SHALL registrare i rifiuti del Guardrail_Layer con `action_type=guardrail_block` e il motivo del blocco in `output_summary`.
5. THE AuditLog SHALL registrare ogni attivazione del fallback LLM con `action_type=llm_fallback`, il provider tentato e il motivo in `input_summary`.
6. THE AuditLog SHALL salvare in `input_summary` e `output_summary` solo riassunti, non dati sensibili grezzi (es. non il testo completo di un documento).
7. THE ACG SHALL esporre nel frontend una `AuditPage` con la lista del log in sola lettura, con filtri per tipo azione e data.

---

### Requisito 20: Storage Layer e Gestione File

**User Story:** Come operatore del sistema, voglio poter configurare il backend di storage (locale, MinIO, S3) tramite variabili d'ambiente senza modificare il codice, così da poter deployare in ambienti diversi (sviluppo, self-hosted, cloud) con la stessa codebase.

#### Acceptance Criteria

1. THE ACG SHALL selezionare l'adapter di storage attivo in base alla variabile d'ambiente `FILE_STORAGE_BACKEND` con valori: `local`, `minio`, `s3`.
2. WHERE `FILE_STORAGE_BACKEND=local`, THE ACG SHALL salvare i file in `LOCAL_STORAGE_PATH` senza richiedere configurazione aggiuntiva, per uso esclusivo in sviluppo e CI.
3. WHERE `FILE_STORAGE_BACKEND=minio`, THE ACG SHALL usare boto3 con endpoint configurato da `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`.
4. WHERE `FILE_STORAGE_BACKEND=s3`, THE ACG SHALL usare boto3 con `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`.
5. THE FileStoragePort SHALL esporre i metodi: `save(file, filename, user_id, content_type) -> FileMetadata`, `get(file_id) -> bytes`, `delete(file_id) -> bool`, `list(user_id, prefix) -> list[FileMetadata]`.
6. THE ACG SHALL costruire il path di storage con il formato `{user_id}/{year}/{month}/{file_id}_{original_filename}`, con la logica centralizzata in `build_storage_key()` per facilitare la futura migrazione multi-tenant (`[TODO: TD-001]`).
7. THE ACG SHALL implementare `MinIOAdapter` e `S3Adapter` con la stessa interfaccia `FileStoragePort`, differenziandosi solo per l'endpoint URL.

---

### Requisito 21: Architettura Esagonale e Protocol Pattern

**User Story:** Come sviluppatore, voglio che il core business logic non dipenda da implementazioni concrete di servizi esterni, così da poter sostituire qualsiasi adapter (LLM, storage, email, parser) senza modificare la logica applicativa.

#### Acceptance Criteria

1. THE ACG SHALL definire tutti i Port come `typing.Protocol` Python in `app/core/ports/`, senza alcun `import` di adapter nel core.
2. THE ACG SHALL implementare il wiring tra Port e adapter in `app/api/deps.py` tramite variabili d'ambiente, non nel core.
3. THE ACG SHALL fornire un'implementazione dummy funzionante per ogni Protocol, usabile nei test unitari senza dipendenze esterne.
4. THE ACG SHALL strutturare la directory secondo l'architettura esagonale: `core/` (domain, ports, services), `agent/` (LangGraph, tools, risk, guardrails), `adapters/` (implementazioni concrete), `api/` (FastAPI routers).
5. THE ACG SHALL usare Pydantic v2 per tutti i modelli di dominio e gli schema API.
6. THE ACG SHALL usare `async/await` su tutti i metodi dei service layer, adapter e nodi LangGraph.
7. THE ACG SHALL usare `structlog` per tutti i log con formato strutturato: `{"event": "...", "user_id": "...", "action": "...", "risk_score": N}`, senza `print()` nel codice.
8. THE ACG SHALL passare `mypy --strict` su tutto il codice del backend.
9. THE CalendarPort SHALL avere un'implementazione stub funzionante nell'MVP (`[TODO: TD-002]` per Google Calendar reale), con interfaccia: `create_event(event, user_id) -> str`, `delete_event(event_id, user_id) -> bool`.

---

### Requisito 22: Frontend — Dashboard e Navigazione

**User Story:** Come utente, voglio un'interfaccia web moderna e reattiva che mi permetta di navigare tra le sezioni principali (inbox, documenti, scadenze, chat, impostazioni) in modo intuitivo, così da gestire l'amministrazione aziendale da un unico punto.

#### Acceptance Criteria

1. THE ACG SHALL implementare il frontend con React 19 + TypeScript + Vite + shadcn/ui + TailwindCSS + React Query (server state) + Zustand (UI state).
2. THE ACG SHALL esporre le seguenti route frontend: `/` (DashboardPage), `/documents` (DocumentsPage), `/documents/:id` (DocumentDetailPage), `/deadlines` (DeadlinesPage), `/agent` (AgentPage), `/confirmations` (ConfirmationsPage), `/email-drafts` (EmailDraftsPage), `/audit` (AuditPage), `/settings` (SettingsPage).
3. THE DashboardPage SHALL implementare il layout inbox-first: Agent Inbox nella colonna principale, widget Scadenze nella colonna laterale, chat in basso.
4. THE ACG SHALL implementare un componente `DeadlineSemaphore` con tre colonne (rosso/giallo/verde), conteggio per colonna, e navigazione a `/deadlines` filtrata al click.
5. THE ACG SHALL implementare una sidebar sinistra con navigazione tra le sezioni e badge notifiche.
6. THE ACG SHALL implementare un header con ricerca globale, campanella notifiche con badge count per notifiche `level=action`, e profilo utente.
7. THE ACG SHALL implementare un componente `AgentChatInterface` con messaggi che mostrano lo stato delle azioni inline: badge per azioni eseguite, link a conferme create, errori inline.
8. THE ACG SHALL implementare la pagina `/settings` con configurazione di: soglie alert scadenze (`red_days`, `yellow_days`, `notify_days_before`), canali notifica per livello, configurazione SMTP, preferenze digest email.

---

### Requisito 23: Impostazioni e Configurazione Utente

**User Story:** Come utente, voglio poter personalizzare le soglie di alert, i canali di notifica e le preferenze del digest, così da adattare il comportamento del sistema alle esigenze specifiche della mia azienda.

#### Acceptance Criteria

1. THE ACG SHALL esporre `GET /settings` che restituisce le preferenze dell'utente autenticato.
2. THE ACG SHALL esporre `PUT /settings` che aggiorna le preferenze dell'utente.
3. THE ACG SHALL supportare la configurazione delle soglie di alert scadenze: `red_days` (default 7), `yellow_days` (default 30), `notify_days_before` (default [30, 7, 3, 1]).
4. THE ACG SHALL supportare la configurazione dei canali di notifica per livello: `red_channels` (default ["inapp", "email"]), `yellow_channels` (default ["inapp"]), `green_channels` (default []).
5. THE ACG SHALL supportare l'abilitazione/disabilitazione del digest email giornaliero nelle preferenze utente.
6. THE ACG SHALL salvare le preferenze utente in `notification_settings` (JSONB) nella tabella `users`.
7. THE ACG SHALL esporre `GET /dashboard/overview` che restituisce: contatori semaforo scadenze, conteggio conferme pendenti, conteggio bozze in attesa, attività recente.

---

### Requisito 24: Trust Progressivo (Schema Phase 0, Logica Phase 3)

**User Story:** Come utente frequente, voglio che il sistema impari dalle mie conferme e riduca progressivamente le richieste di verifica per i campi che ho storicamente confermato senza modifiche, così da ridurre il carico di revisione nel tempo.

#### Acceptance Criteria

1. THE ACG SHALL creare la tabella `user_extraction_trust` nella migration iniziale di Phase 0 con campi: `user_id`, `document_type`, `field_name`, `total_extractions`, `confirmed_without_edit`, `edited_extractions`, `accuracy` (colonna generata), `last_updated`.
2. WHEN l'utente interagisce con una ReviewCard confermando un campo senza modificarlo, THE ACG SHALL incrementare `confirmed_without_edit` e `total_extractions` per la coppia `(user_id, document_type, field_name)`.
3. WHEN l'utente interagisce con una ReviewCard modificando il valore di un campo, THE ACG SHALL incrementare `edited_extractions` e `total_extractions` per la coppia `(user_id, document_type, field_name)`.
4. WHILE il sistema è in Phase 0, 1 o 2, THE RiskEngine SHALL ignorare i dati di `user_extraction_trust` e usare le soglie base da `rules.yaml`.
5. WHEN il sistema è in Phase 3, THE RiskEngine SHALL esporre un metodo `effective_threshold(user_id, document_type, field_name) -> float` che abbassa la soglia base in proporzione all'`accuracy` storica dell'utente per quel campo.
6. THE ACG SHALL usare la chiave primaria composta `(user_id, document_type, field_name)` per garantire un record per combinazione utente/tipo documento/campo.

---

### Requisito 25: Parser — Round-Trip e Qualità Estrazione

**User Story:** Come sviluppatore, voglio che il sistema di parsing sia verificabile e affidabile, così da poter rilevare regressioni nell'estrazione dei dati prima che raggiungano la produzione.

#### Acceptance Criteria

1. THE DocumentParserPort SHALL esporre i metodi: `can_parse(content_type, filename) -> bool` e `parse(file: bytes, filename: str) -> ParsedDocument`.
2. THE ParsedDocument SHALL contenere: `text` (testo completo), `tables` (tabelle strutturate), `metadata` (titolo, date, autore), `raw_pages` (testo per pagina), `confidence` (float 0.0–1.0).
3. THE ParserRegistry SHALL selezionare il parser corretto tramite `can_parse()` in base a Content-Type e nome file, senza logica di selezione hardcodata nei service.
4. WHEN LlamaParse restituisce `confidence < 0.60`, THE ParserWithFallback SHALL tentare Unstructured e restituire il `ParsedDocument` con confidence più alta tra i due risultati.
5. FOR ALL documenti parsati con successo e poi serializzati in JSON, THE DocumentPipeline SHALL essere in grado di ricostruire un `ParsedDocument` equivalente dalla rappresentazione JSON (proprietà round-trip della serializzazione dei metadati estratti).
6. THE ACG SHALL includere test unitari per ogni parser con almeno un documento di esempio per tipo supportato (PDF strutturato, PDF scansionato, XLSX, CSV).

---

### Requisito 26: Vincoli e Azioni Vietate nell'MVP

**User Story:** Come utente, voglio che il sistema mi informi chiaramente quando una richiesta non è supportata nell'MVP, così da non aspettarmi funzionalità non disponibili e capire il perché del rifiuto.

#### Acceptance Criteria

1. IF l'utente richiede l'invio di comunicazioni a enti pubblici (Agenzia Entrate, INPS, SDI per invio), THEN THE ACG SHALL rifiutare la richiesta con un messaggio esplicativo e non creare alcuna azione correlata.
2. IF l'utente richiede l'esecuzione di pagamenti o bonifici di qualsiasi tipo, THEN THE ACG SHALL rifiutare la richiesta con un messaggio esplicativo.
3. IF l'utente richiede la modifica di software gestionali o contabili, THEN THE ACG SHALL rifiutare la richiesta con un messaggio esplicativo.
4. IF l'utente richiede un consiglio fiscale interpretativo nel caso specifico, THEN THE ACG SHALL rispondere descrivendo la normativa generale senza interpretarla nel caso specifico, e suggerire di consultare un commercialista.
5. THE ACG SHALL implementare le funzionalità marcate `[DEFERRED]` come stub con interfaccia reale ma implementazione dummy: multi-tenancy RLS, n8n integration, ML Risk Scoring, Google Calendar adapter, RBAC avanzato, billing/subscription, file encryption at rest.
6. THE ACG SHALL includere commenti `[TODO: TD-XXX]` nel codice per ogni implementazione stub, referenziando il Technical Debt Register del blueprint.
7. THE ACG SHALL non implementare né lasciare stub per le funzionalità `[FORBIDDEN_MVP]`: queste devono essere rifiutate attivamente a runtime dal Guardrail_Layer.

---

### Requisito 27: Osservabilità e Logging Strutturato

**User Story:** Come sviluppatore e operatore, voglio che il sistema produca log strutturati e tracce delle chiamate LLM, così da poter diagnosticare problemi in produzione e ottimizzare le performance dell'agente.

#### Acceptance Criteria

1. THE ACG SHALL usare `structlog` per tutti i log del backend con formato JSON strutturato contenente almeno: `event`, `user_id`, `action`, `risk_score` dove applicabile.
2. THE ACG SHALL registrare nell'AuditLog ogni chiamata LLM con: `llm_model` usato, `action_type`, `status` (success/fallback/failed).
3. WHERE `LANGSMITH_ENABLED=true`, THE ACG SHALL inviare le tracce LangGraph a LangSmith usando `LANGSMITH_API_KEY` (Phase 3).
4. THE ACG SHALL esporre health check endpoint `GET /health` che verifica la connettività a: database PostgreSQL, storage backend configurato, e restituisce `{ status: "ok" | "degraded", checks: {...} }`.
5. THE ACG SHALL configurare il livello di log tramite variabile d'ambiente `LOG_LEVEL` (default: `INFO`).
6. THE ACG SHALL non loggare mai valori di segreti (API key, password, token JWT) nei log strutturati, referenziandoli solo per nome.

---

### Requisito 28: Testing e Qualità del Codice

**User Story:** Come sviluppatore, voglio che il progetto abbia una suite di test automatizzati che verifichi il comportamento corretto dei componenti critici, così da poter fare refactoring e aggiungere funzionalità con fiducia.

#### Acceptance Criteria

1. THE ACG SHALL includere test unitari per ogni service del core (`document_service`, `deadline_service`, `email_draft_service`, `notification_service`, `audit_service`) usando mock che implementano i Protocol corrispondenti.
2. THE ACG SHALL includere test unitari per il `RiskEngine` che verificano il calcolo del risk score per ogni livello (0-5) con e senza modificatori di contesto.
3. THE ACG SHALL includere test unitari per il `Guardrail_Layer` che verificano il blocco delle azioni in Blacklist e delle violazioni della Constitution.
4. THE ACG SHALL includere test di integrazione per la DocumentPipeline con file di esempio reali (PDF, XLSX, CSV).
5. THE ACG SHALL includere test per ogni Protocol che verificano l'interfaccia con un'implementazione dummy.
6. FOR ALL workflow template registrati nel WorkflowTemplateRegistry, THE ACG SHALL includere almeno un test che verifica l'esecuzione completa del workflow con argomenti validi usando adapter mock.
7. THE ACG SHALL strutturare i test in `tests/unit/` (test core con mock dei port) e `tests/integration/` (test con adapter reali).
8. FOR ALL endpoint REST esposti, THE ACG SHALL includere test che verificano: risposta corretta per input valido, risposta HTTP 401 per richieste non autenticate, risposta HTTP 422 per input malformato.

---

## Note Implementative

### Ordine di Implementazione Raccomandato

1. **Phase 0 — Foundation**: Protocol + dummy adapter → schema DB completo → Docker Compose → auth JWT → WorkflowTemplateRegistry stub.
2. **Phase 1 — Document Core**: upload documenti → parsing pipeline → classificazione + estrazione → confidence gate → ReviewCard → TriageGraph per `DOCUMENT_UPLOADED` → AgentInboxItem → frontend inbox-first.
3. **Phase 2 — Intelligence + Inbox**: TriageGraph completo → WorkflowGraph con 3 template → DailyDigestService + scheduler → chat agent con intent mapping → deadline engine → notification system → email drafting → guardrails.
4. **Phase 3 — Polish & Production**: trust progressivo → detect_patterns() con LLM → workflow template aggiuntivi → digest email HTML → LangSmith tracing → Docker Compose production-ready.

### Vincoli Architetturali Non Negoziabili

- Nessun `import` di adapter nel core (`app/core/`).
- Nessun accesso diretto al DB nei nodi LangGraph: sempre via service layer.
- Nessun global state nell'agent: tutto passa attraverso `AgentState`.
- Nessun prompt hardcodato nel codice Python: sempre file `.md` in `app/agent/prompts/`.
- Nessun retry automatico su azioni di Risk_Level ≥ 4.
- `mypy --strict` deve passare su tutto il backend.
