# Requirements Document

## Introduction

Questo documento specifica i requisiti per l'evoluzione di ACG (Admin & Compliance Guardian) lungo 8 assi di miglioramento. L'obiettivo è trasformare ACG da assistente reattivo a sistema proattivo agent-centric, con monitoraggio passivo delle sorgenti G Suite, analisi intelligente dei documenti, correlazione cross-document, escalation progressiva delle notifiche, reportistica esportabile, integrazione contestuale G Suite, navigazione riprogettata e solidità UX trasversale.

I principi trasversali che permeano tutti i requisiti sono:
- **Agent-centric UI**: l'agente è il centro gravitazionale, sempre attivo e visibile
- **Adaptive canvas**: le viste cambiano in base all'attività corrente (max 2-3 zone dinamiche per vista)
- **HITL**: ogni azione con effetti esterni richiede approvazione esplicita con preview chiara
- **Zero hallucination UI**: distinzione visiva tra dati estratti (con source link e confidence) e dati inferiti/suggeriti
- **Real-time**: notifiche, stato processing e aggiornamenti da Drive/Gmail/Calendar sono live

---

## Glossary

- **ACG**: Admin & Compliance Guardian — il sistema oggetto di questo documento.
- **Agent**: il componente AI basato su LangGraph che monitora, analizza e propone azioni proattivamente.
- **Ingest_Pipeline**: pipeline di acquisizione passiva che monitora Gmail, Google Drive e Google Calendar per nuovi documenti ed eventi.
- **Source_Monitor**: componente che esegue polling periodico sulle sorgenti configurate (cartelle Drive, label Gmail, calendari).
- **Risky_Clause_Detector**: componente AI che analizza contratti e identifica clausole potenzialmente rischiose con attribuzione al testo sorgente.
- **Cross_Document_Engine**: componente che correla documenti tra loro identificando relazioni, conflitti e allegati mancanti.
- **Escalation_Engine**: componente che gestisce la progressione delle notifiche con cambio di destinatario o canale dopo timeout configurabili.
- **Report_Generator**: componente che produce report PDF/Excel con dati tracciabili a documenti reali.
- **Quick_View_Panel**: pannello contestuale che mostra file Drive e eventi Calendar per import selettivo in ACG.
- **Adaptive_Canvas**: sistema di layout dinamico che adatta le zone della vista in base all'attività corrente dell'utente.
- **Confirmation_Flow**: pattern UX unificato per tutte le azioni con effetti esterni, con preview e source attribution.
- **HITL**: Human-In-The-Loop — meccanismo di approvazione esplicita per azioni con effetti esterni.
- **Confidence_Indicator**: indicatore visivo che comunica il livello di certezza dell'AI su un dato estratto o inferito.
- **Source_Attribution**: collegamento visivo tra un dato mostrato e il documento/pagina/paragrafo da cui è stato estratto.
- **Escalation_Rule**: regola configurabile che definisce tempi, destinatari e canali per la progressione delle notifiche.
- **Dossier**: fascicolo logico che raggruppa documenti correlati (es. contratto quadro + fatture + allegati).
- **PMI**: Piccola e Media Impresa — target utente del sistema.
- **Drive_Adapter**: adapter per Google Drive API che gestisce listing, download e upload di file.
- **Gmail_Adapter**: adapter per Gmail API che gestisce lettura email, invio e monitoraggio label.
- **Calendar_Adapter**: adapter per Google Calendar API che gestisce lettura, creazione e modifica eventi.
- **Calendar_Event_Creation**: azione dell'agente che crea un evento su Google Calendar con HITL obbligatorio (risk level 3).
- **WebSocket_Channel**: canale di comunicazione real-time tra backend e frontend per aggiornamenti live.
- **Processing_Feed**: feed in tempo reale che mostra lo stato di elaborazione dei documenti in ingresso.

---

## Requirements

---

### Requirement 1: Configurazione Sorgenti Monitorate

**User Story:** Come amministratore di PMI, voglio configurare quali cartelle Drive, label Gmail e calendari Google l'agente deve monitorare, così da ricevere automaticamente i documenti rilevanti senza doverli caricare manualmente.

#### Acceptance Criteria

1. THE ACG SHALL esporre una vista "Sorgenti monitorate" che permette di aggiungere, modificare e rimuovere sorgenti di tipo: cartella Google Drive, label Gmail, calendario Google Calendar.
2. WHEN l'utente aggiunge una sorgente Drive, THE ACG SHALL richiedere la selezione di una cartella tramite Google Picker API e salvare `folder_id`, `folder_name` e `polling_interval` (default: 15 minuti, range valido: 5 minuti–24 ore).
3. WHEN l'utente aggiunge una sorgente Gmail, THE ACG SHALL richiedere la selezione di una o più label e salvare `label_ids`, `label_names` e `polling_interval` (default: 10 minuti, range valido: 5 minuti–24 ore).
4. WHEN l'utente aggiunge una sorgente Calendar, THE ACG SHALL richiedere la selezione di un calendario e salvare `calendar_id`, `calendar_name` e `lookahead_days` (default: 30 giorni, range valido: 7–90 giorni).
5. THE ACG SHALL mostrare per ogni sorgente configurata: stato connessione live (connesso/errore/in sincronizzazione), timestamp dell'ultimo polling riuscito, e conteggio documenti importati dall'ultima sincronizzazione.
6. IF le credenziali OAuth per una sorgente risultano scadute o revocate, THEN THE ACG SHALL mostrare lo stato "Disconnesso" con un pulsante "Riconnetti" che avvia il flusso OAuth senza perdere la configurazione della sorgente.
7. THE ACG SHALL validare che l'utente abbia concesso i permessi OAuth necessari (scope `drive.readonly`, `gmail.readonly`, `calendar.readonly`, e opzionalmente `calendar.events` per la creazione eventi e `gmail.send` per l'invio email) prima di salvare una sorgente; IF i permessi sono insufficienti, THEN THE ACG SHALL mostrare un messaggio che indica quali permessi aggiuntivi sono necessari.

---

### Requirement 2: Polling e Ingest Passivo da Drive e Gmail

**User Story:** Come amministratore di PMI, voglio che l'agente rilevi e processi automaticamente i nuovi documenti nelle sorgenti configurate, così da non dover caricare manualmente ogni fattura o contratto ricevuto.

#### Acceptance Criteria

1. THE Source_Monitor SHALL eseguire polling su ogni sorgente configurata alla frequenza definita dall'utente, utilizzando APScheduler per la pianificazione dei job.
2. WHEN il Source_Monitor rileva un nuovo file in una cartella Drive monitorata, THE Ingest_Pipeline SHALL scaricare il file tramite Drive_Adapter, creare un record `documents` con `source=drive` e `source_ref_id=file_id`, e avviare la DocumentPipeline esistente.
3. WHEN il Source_Monitor rileva una nuova email con allegati in una label Gmail monitorata, THE Ingest_Pipeline SHALL scaricare ogni allegato tramite Gmail_Adapter, creare un record `documents` per ogni allegato con `source=gmail` e `source_ref_id=message_id`, e avviare la DocumentPipeline per ciascuno.
4. THE Source_Monitor SHALL mantenere un registro `last_sync_token` per ogni sorgente per evitare di ri-processare documenti già acquisiti; IF il sync token è invalidato dal provider, THEN THE Source_Monitor SHALL eseguire una sincronizzazione completa e loggare l'evento nell'AuditLog.
5. IF il polling di una sorgente fallisce per 3 tentativi consecutivi, THEN THE Source_Monitor SHALL impostare lo stato della sorgente a "errore", creare una notifica `level=warning` per l'utente, e sospendere il polling fino a intervento manuale o riconnessione OAuth.
6. THE Ingest_Pipeline SHALL ignorare file con formati non supportati (non PDF, XLS, XLSX, CSV) rilevati nelle sorgenti, registrando un log `level=debug` senza creare notifiche per l'utente.
7. THE Source_Monitor SHALL processare al massimo 10 file per ciclo di polling per sorgente, accodando i rimanenti al ciclo successivo, per evitare sovraccarico del sistema.
8. WHEN un documento viene acquisito da una sorgente passiva, THE ACG SHALL mostrare nel Processing_Feed lo stato in tempo reale: "In analisi", "Completato", "Richiede attenzione umana".

---

### Requirement 3: Rilevamento Eventi Calendar e Proposizione Scadenze

**User Story:** Come amministratore di PMI, voglio che l'agente rilevi automaticamente eventi rilevanti dal mio Google Calendar (scadenze contrattuali, appuntamenti con fornitori) e me li proponga come scadenze tracciate in ACG, così da centralizzare tutte le deadline in un unico sistema.

#### Acceptance Criteria

1. WHEN il Source_Monitor rileva un nuovo evento in un calendario monitorato, THE Ingest_Pipeline SHALL analizzare titolo, descrizione e partecipanti dell'evento per determinare se è rilevante per il dominio amministrativo (scadenze fiscali, rinnovi contrattuali, appuntamenti con fornitori/clienti).
2. WHEN un evento Calendar è classificato come rilevante con confidence >= 0.70, THE ACG SHALL creare un AgentInboxItem con azione suggerita "Importa come scadenza" che include: data evento, titolo proposto per la scadenza, e categoria suggerita.
3. THE ACG SHALL richiedere approvazione HITL prima di creare una scadenza da un evento Calendar; la preview SHALL mostrare: titolo originale dell'evento, data, la scadenza proposta con i campi pre-compilati, e la fonte (nome calendario + link all'evento).
4. IF un evento Calendar ha confidence < 0.70 per la rilevanza amministrativa, THEN THE Ingest_Pipeline SHALL ignorare l'evento senza creare notifiche, registrando un log `level=debug`.
5. THE Ingest_Pipeline SHALL evitare duplicati confrontando `calendar_event_id` con le scadenze esistenti; IF una scadenza derivata da un evento Calendar esiste già, THEN THE Ingest_Pipeline SHALL verificare se l'evento è stato modificato e, in caso affermativo, proporre l'aggiornamento della scadenza tramite HITL.

---

### Requirement 4: Processing Feed Real-Time

**User Story:** Come utente, voglio vedere in tempo reale lo stato di elaborazione dei documenti in arrivo dalle sorgenti monitorate, così da sapere cosa l'agente sta processando senza dover ricaricare la pagina.

#### Acceptance Criteria

1. THE ACG SHALL esporre un endpoint WebSocket `/ws/processing-feed` che emette eventi di stato per ogni documento in elaborazione: `ingesting`, `parsing`, `classifying`, `extracting`, `completed`, `needs_attention`, `failed`.
2. THE ACG SHALL mostrare nel canvas principale una sezione "In arrivo" che elenca i documenti in elaborazione con: nome file, sorgente di provenienza (icona Drive/Gmail/Calendar), stato corrente con indicatore di progresso, e timestamp di inizio elaborazione.
3. WHEN un documento completa l'elaborazione con successo, THE Processing_Feed SHALL mostrare un riepilogo compatto (tipo documento rilevato, campi estratti principali, scadenze trovate) per 30 secondi prima di archiviare l'item nel feed.
4. WHEN un documento richiede attenzione umana (confidence sotto soglia, parsing fallito), THE Processing_Feed SHALL evidenziare l'item con indicatore visivo "Richiede attenzione" e link diretto alla ReviewCard o al dettaglio errore.
5. THE Processing_Feed SHALL mostrare al massimo 20 item recenti, con possibilità di espandere lo storico completo delle ultime 24 ore.

---

### Requirement 5: Rilevamento Clausole Rischiose nei Contratti

**User Story:** Come amministratore di PMI, voglio che l'agente evidenzi automaticamente le clausole potenzialmente rischiose quando carico un contratto, così da non dover leggere ogni riga per identificare rinnovi automatici, penali o limitazioni di responsabilità.

#### Acceptance Criteria

1. WHEN un documento viene classificato come `contratto`, THE Risky_Clause_Detector SHALL analizzare il testo per identificare clausole nelle categorie: rinnovo automatico, penali, limitazioni di responsabilità, clausole di recesso, clausole di esclusiva, clausole di non concorrenza.
2. THE Risky_Clause_Detector SHALL associare a ogni clausola rilevata: la categoria di rischio, il testo esatto della clausola nel documento sorgente, il riferimento alla pagina e paragrafo, un livello di severità (alto/medio/basso), e un Confidence_Score.
3. THE Risky_Clause_Detector SHALL generare per ogni clausola rilevata una spiegazione in linguaggio semplice (plain-language) di massimo 200 caratteri che descrive l'implicazione pratica per l'utente.
4. IF il Confidence_Score di una clausola rilevata è inferiore a 0.75, THEN THE ACG SHALL mostrare la clausola con un Confidence_Indicator visivo "Interpretazione incerta" e distinguerla visivamente dalle clausole ad alta confidence.
5. THE ACG SHALL mostrare le clausole rischiose esclusivamente con Source_Attribution verificabile: ogni highlight nella vista documento deve essere cliccabile per navigare al testo esatto nel documento originale.
6. THE Risky_Clause_Detector SHALL operare con risk score 0 (sola lettura e analisi), senza creare PendingConfirmation per l'analisi stessa; le azioni suggerite derivanti dall'analisi (es. "Negozia modifica clausola") seguono il normale flusso HITL.

---

### Requirement 6: Vista Analisi Contratto con Adaptive Canvas

**User Story:** Come utente, voglio visualizzare l'analisi delle clausole rischiose in un layout dedicato quando apro un contratto, così da avere una visione d'insieme dei rischi senza dover navigare tra schermate diverse.

#### Acceptance Criteria

1. WHEN l'utente apre un documento di tipo `contratto` che ha completato l'analisi clausole, THE Adaptive_Canvas SHALL adattare il layout in due zone: zona principale con il documento e highlight inline delle clausole, zona laterale con il pannello riepilogo clausole.
2. THE ACG SHALL mostrare nel pannello laterale la lista delle clausole rilevate raggruppate per categoria di rischio, ordinate per severità decrescente, con: badge colorato per severità (rosso=alto, arancio=medio, giallo=basso), testo della spiegazione plain-language, e Confidence_Indicator.
3. WHEN l'utente clicca una clausola nel pannello laterale, THE ACG SHALL scrollare il documento alla posizione esatta della clausola e evidenziarla con animazione di focus.
4. WHEN l'utente clicca un highlight nel documento, THE ACG SHALL espandere nel pannello laterale il dettaglio della clausola corrispondente con: testo completo estratto, spiegazione, confidence, e azioni suggerite (es. "Segna come accettata", "Crea reminder per rinegoziazione").
5. IF un contratto non ha clausole rischiose rilevate, THEN THE ACG SHALL mostrare nel pannello laterale un messaggio "Nessuna clausola rischiosa rilevata" con il Confidence_Score complessivo dell'analisi e la nota "L'analisi automatica potrebbe non rilevare tutte le clausole — si consiglia revisione legale per contratti critici".

---

### Requirement 7: Correlazione Cross-Document

**User Story:** Come amministratore di PMI, voglio che l'agente identifichi automaticamente le relazioni tra documenti (fattura collegata a contratto quadro, allegati mancanti, contraddizioni tra versioni), così da avere una visione completa di ogni fascicolo senza dover cercare manualmente i collegamenti.

#### Acceptance Criteria

1. WHEN un nuovo documento viene processato, THE Cross_Document_Engine SHALL cercare correlazioni con i documenti esistenti dello stesso utente basandosi su: entità condivise (fornitore, cliente, P.IVA), riferimenti espliciti nel testo (numero contratto, numero fattura), e sovrapposizione temporale.
2. THE Cross_Document_Engine SHALL classificare ogni correlazione trovata in una delle categorie: `derivato_da` (fattura da contratto), `versione_di` (aggiornamento di documento precedente), `allegato_di` (allegato mancante o presente), `in_conflitto_con` (dati contraddittori tra documenti).
3. THE Cross_Document_Engine SHALL associare a ogni correlazione: la Source_Attribution con i passaggi specifici dei due documenti che giustificano la correlazione, un Confidence_Score, e la categoria.
4. WHEN il Cross_Document_Engine rileva una correlazione di tipo `in_conflitto_con`, THE ACG SHALL creare un AgentInboxItem con urgency `today` che include: descrizione del conflitto, preview side-by-side dei passaggi in conflitto con citazione esatta da entrambi i documenti, e azioni suggerite per la risoluzione.
5. THE Cross_Document_Engine SHALL operare con risk score 1 (lettura + scrittura interna correlazioni), senza effetti esterni.
6. THE ACG SHALL distinguere visivamente le correlazioni per livello di certezza: "Correlazione certa" (Confidence >= 0.85, basata su riferimenti espliciti) e "Correlazione probabile" (Confidence 0.60–0.85, basata su inferenza semantica); correlazioni con Confidence < 0.60 non vengono mostrate.

---

### Requirement 8: Vista Relazioni e Dossier

**User Story:** Come utente, voglio visualizzare le relazioni tra documenti in una vista strutturata e capire se un fascicolo è completo, così da identificare rapidamente allegati mancanti o incongruenze.

#### Acceptance Criteria

1. THE ACG SHALL esporre una vista "Relazioni" accessibile dal dettaglio documento che mostra tutte le correlazioni del documento corrente come lista strutturata con: documento correlato (nome, tipo, data), tipo di correlazione, Confidence_Indicator, e link ai passaggi sorgente.
2. THE ACG SHALL esporre una funzionalità "Dossier" che raggruppa automaticamente documenti correlati in fascicoli logici (es. contratto quadro + tutte le fatture derivate + allegati), con indicazione di completezza.
3. WHEN un Dossier risulta incompleto, THE ACG SHALL mostrare la lista degli elementi mancanti distinguendo: "Mancante con certezza" (riferimento esplicito a documento non presente nel sistema) e "Probabilmente mancante" (inferenza basata su pattern tipici del tipo di fascicolo).
4. WHEN l'utente visualizza un Dossier incompleto, THE ACG SHALL suggerire azioni per completarlo: "Cerca in Drive" (ricerca nelle sorgenti monitorate), "Richiedi al fornitore" (bozza email), con ogni azione soggetta al normale flusso HITL.
5. THE ACG SHALL aggiornare automaticamente i Dossier quando nuovi documenti vengono processati e correlati, notificando l'utente se un Dossier precedentemente incompleto diventa completo.

---

### Requirement 9: Configurazione Regole di Escalation

**User Story:** Come amministratore di PMI, voglio configurare regole di escalation per le notifiche delle scadenze, così che se non confermo una scadenza entro un certo tempo, il sistema escali automaticamente cambiando destinatario o canale.

#### Acceptance Criteria

1. THE ACG SHALL esporre una vista "Regole Escalation" che permette di creare, modificare e eliminare regole di escalation per tipo di scadenza (fiscale, contrattuale, pagamento, generico).
2. THE Escalation_Rule SHALL definire una sequenza di step con: tempo di attesa prima dell'escalation (range: 1 ora–7 giorni), canale di notifica (in-app, email, evento calendario), destinatario (utente corrente, email specifica, calendario specifico), e messaggio template.
3. WHEN l'utente crea o modifica una Escalation_Rule, THE ACG SHALL mostrare un'anteprima visiva del flusso di escalation completo (timeline con step, tempi e destinatari) prima di salvare.
4. THE ACG SHALL fornire template predefiniti di escalation per i tipi di scadenza più comuni: "Scadenza fiscale" (notifica in-app → email utente dopo 4h → email commercialista dopo 24h), "Pagamento fornitore" (notifica in-app → email utente dopo 8h → email responsabile dopo 48h).
5. THE Escalation_Rule SHALL supportare al massimo 5 step di escalation per regola, con validazione che ogni step successivo abbia un tempo di attesa maggiore del precedente.

---

### Requirement 10: Esecuzione Escalation con HITL per Email

**User Story:** Come utente, voglio che il sistema esegua automaticamente le escalation configurate ma mi chieda sempre conferma prima di inviare email reali, così da mantenere il controllo sulle comunicazioni esterne.

#### Acceptance Criteria

1. WHEN una scadenza con `status=active` non viene confermata (nessuna azione dall'utente sull'AgentInboxItem correlato) entro il tempo definito nel primo step della Escalation_Rule applicabile, THE Escalation_Engine SHALL avviare la sequenza di escalation.
2. WHEN uno step di escalation prevede una notifica in-app, THE Escalation_Engine SHALL creare la notifica direttamente senza HITL (risk score 1).
3. WHEN uno step di escalation prevede l'invio di un'email, THE Escalation_Engine SHALL creare una PendingConfirmation con: anteprima completa dell'email (destinatario, oggetto, corpo), fonte della scadenza (documento originale con link), e motivazione dell'escalation ("Nessuna azione dopo X ore"); l'email viene inviata solo dopo approvazione esplicita.
4. WHEN uno step di escalation prevede la creazione di un evento calendario, THE Escalation_Engine SHALL creare una PendingConfirmation con: anteprima dell'evento (titolo, data, calendario, descrizione con riferimento alla scadenza), motivazione dell'escalation; l'evento viene creato solo dopo approvazione esplicita tramite il flusso standard di creazione eventi Calendar (Requirement 13).
4. THE ACG SHALL esporre una vista "Stato Notifiche" che mostra per ogni scadenza attiva: lo step di escalation corrente, lo storico delle notifiche inviate (con timestamp e stato lettura se disponibile da Gmail), e il prossimo step pianificato con countdown.
5. IF l'utente conferma la scadenza (esegue un'azione sull'AgentInboxItem correlato) durante la sequenza di escalation, THEN THE Escalation_Engine SHALL interrompere la sequenza e registrare la risoluzione nell'AuditLog.
6. IF l'invio email fallisce (errore Gmail API, destinatario non valido), THEN THE Escalation_Engine SHALL creare una notifica in-app `level=warning` con il dettaglio dell'errore e un'azione suggerita (es. "Verifica indirizzo email", "Riprova invio").
7. THE Escalation_Engine SHALL inviare email reali esclusivamente tramite Gmail_Adapter con scope `gmail.send`, utilizzando l'account Gmail connesso dall'utente.

---

### Requirement 11: Generazione Report Esportabili

**User Story:** Come amministratore di PMI, voglio generare report PDF o Excel con le scadenze di un periodo per il commercialista o la direzione, così da avere documentazione strutturata da condividere senza dover compilare manualmente fogli di calcolo.

#### Acceptance Criteria

1. THE Report_Generator SHALL esporre una vista "Report" con: selezione periodo (date inizio/fine), filtri per tipo scadenza e stato, selezione formato output (PDF, Excel), e anteprima live del report prima della generazione.
2. THE Report_Generator SHALL includere nel report esclusivamente dati presenti nel sistema e tracciabili a documenti reali; ogni riga del report SHALL includere il riferimento al documento sorgente.
3. THE ACG SHALL fornire template di report predefiniti: "Scadenze mensili" (tutte le scadenze del mese con stato), "Riepilogo trimestrale fisco" (scadenze fiscali del trimestre), "Contratti in scadenza" (contratti con rinnovo nei prossimi 90 giorni).
4. WHEN l'utente genera un report, THE Report_Generator SHALL mostrare l'anteprima nel canvas prima di procedere all'export, permettendo di modificare filtri e rigenerare.
5. THE Report_Generator SHALL supportare la personalizzazione dei template: selezione colonne visibili, ordinamento, raggruppamento per categoria.

---

### Requirement 12: Export Report verso Drive e Gmail con HITL

**User Story:** Come utente, voglio esportare i report generati direttamente su Google Drive o inviarli via email al commercialista, con conferma esplicita prima di ogni azione esterna.

#### Acceptance Criteria

1. WHEN l'utente sceglie "Esporta su Drive", THE ACG SHALL mostrare una PendingConfirmation con: anteprima del file da caricare (nome, formato, dimensione), cartella di destinazione selezionabile tramite picker, e preview del path completo su Drive.
2. WHEN l'utente approva l'export su Drive, THE ACG SHALL caricare il file tramite Drive_Adapter con scope `drive.file`, creare il file nella cartella selezionata, e mostrare un link diretto al file creato su Google Drive.
3. WHEN l'utente sceglie "Invia via email", THE ACG SHALL mostrare una PendingConfirmation con: anteprima completa dell'email (destinatario editabile, oggetto pre-compilato, corpo con riepilogo, allegato), permettendo modifiche prima dell'invio.
4. WHEN l'utente approva l'invio email del report, THE ACG SHALL inviare l'email con allegato tramite Gmail_Adapter con scope `gmail.send` e registrare l'invio nell'AuditLog.
5. IF l'upload su Drive o l'invio email fallisce, THEN THE ACG SHALL mostrare il dettaglio dell'errore con azione suggerita "Riprova" senza perdere il report generato.
6. THE ACG SHALL mantenere uno storico dei report generati con: data generazione, parametri utilizzati, destinazione export (Drive path o email destinatario), accessibile dalla vista Report.


---

### Requirement 13: Creazione Eventi Calendar dall'Agente

**User Story:** Come amministratore di PMI, voglio che l'agente possa creare eventi sul mio Google Calendar (reminder per scadenze, appuntamenti suggeriti) con la mia approvazione esplicita, così da avere le deadline sincronizzate direttamente nel calendario che uso quotidianamente.

#### Acceptance Criteria

1. WHEN l'agente identifica una scadenza che beneficerebbe di un reminder su Calendar (scadenze fiscali, rinnovi contrattuali, pagamenti), THE ACG SHALL proporre la creazione di un evento Calendar tramite AgentInboxItem con azione "Crea reminder su Calendar".
2. THE ACG SHALL richiedere approvazione HITL (risk level 3) prima di creare qualsiasi evento su Google Calendar; la PendingConfirmation SHALL mostrare: titolo evento proposto, data e ora, calendario di destinazione, descrizione pre-compilata con riferimento alla scadenza sorgente, e reminder configurati (default: 1 giorno prima e 1 ora prima).
3. WHEN l'utente approva la creazione di un evento Calendar, THE ACG SHALL creare l'evento tramite Calendar_Adapter con scope `calendar.events`, salvare il `calendar_event_id` come riferimento nella scadenza correlata, e mostrare un link diretto all'evento creato.
4. THE ACG SHALL permettere all'utente di modificare nella preview HITL: titolo, data/ora, calendario di destinazione, descrizione, e configurazione reminder prima di approvare la creazione.
5. WHEN una scadenza con evento Calendar associato viene completata o annullata in ACG, THE ACG SHALL proporre tramite HITL la cancellazione o l'aggiornamento dell'evento Calendar corrispondente.
6. IF la creazione dell'evento Calendar fallisce (errore API, permessi insufficienti), THEN THE ACG SHALL mostrare il dettaglio dell'errore con azione suggerita "Verifica permessi Calendar" e mantenere la scadenza attiva in ACG senza evento associato.
7. THE ACG SHALL validare che l'utente abbia concesso il permesso OAuth `calendar.events` (scope di scrittura) prima di proporre la creazione di eventi; IF il permesso non è presente, THEN THE ACG SHALL mostrare un prompt per concedere il permesso aggiuntivo.

---

### Requirement 14: Quick View Drive — Pannello Contestuale File

**User Story:** Come utente, voglio vedere i file recenti di Google Drive in un pannello contestuale dentro ACG e decidere quali importare, così da non dover uscire dall'applicazione per verificare cosa è disponibile nelle mie cartelle.

#### Acceptance Criteria

1. THE Quick_View_Panel SHALL mostrare un pannello "Drive" con: file recenti delle cartelle monitorate (ultimi 30 giorni), organizzati per cartella, con nome file, data modifica, dimensione, e tipo.
2. THE Quick_View_Panel SHALL permettere la selezione multipla di file tramite checkbox per import selettivo; l'import effettivo avviene solo dopo conferma esplicita con preview dei file selezionati.
3. WHEN l'utente conferma l'import di file dal Quick_View_Panel, THE Ingest_Pipeline SHALL processare ogni file selezionato attraverso la DocumentPipeline standard, mostrando il progresso nel Processing_Feed.
4. THE Quick_View_Panel SHALL indicare visivamente i file già importati in ACG (badge "Già importato" con data di import) per evitare duplicati accidentali.
5. THE Quick_View_Panel SHALL supportare la navigazione nelle sottocartelle delle cartelle monitorate e la ricerca per nome file.
6. THE Quick_View_Panel SHALL apparire nel canvas contestuale quando rilevante (es. durante la creazione di un Dossier o la ricerca di allegati mancanti), non come tab separata permanente nella navigazione principale.

---

### Requirement 15: Quick View Calendar — Pannello Contestuale Eventi

**User Story:** Come utente, voglio vedere gli eventi dei prossimi 30 giorni dal mio Google Calendar in un pannello contestuale e trasformarli in scadenze tracciate in ACG, così da centralizzare tutte le deadline senza dover copiare manualmente le date.

#### Acceptance Criteria

1. THE Quick_View_Panel SHALL mostrare un pannello "Calendar" con: eventi dei prossimi 30 giorni dai calendari monitorati, organizzati cronologicamente, con titolo, data/ora, e partecipanti.
2. THE Quick_View_Panel SHALL permettere di flaggare singoli eventi per trasformarli in scadenze tracciate; per ogni evento flaggato, THE ACG SHALL mostrare un'anteprima di come verrà importata la scadenza (titolo, data, categoria suggerita) prima della conferma.
3. WHEN l'utente conferma la creazione di una scadenza da un evento Calendar, THE ACG SHALL creare la scadenza con `source=calendar` e `source_ref_id=event_id`, e collegare l'evento originale come Source_Attribution.
4. THE Quick_View_Panel SHALL indicare visivamente gli eventi già importati come scadenze in ACG (badge "Tracciato" con link alla scadenza).
5. THE Quick_View_Panel SHALL filtrare di default gli eventi che il sistema classifica come non rilevanti per il dominio amministrativo (es. eventi personali), con possibilità di mostrare tutti gli eventi tramite toggle "Mostra tutti".

---

### Requirement 16: Architettura Navigazione Agent-Centric

**User Story:** Come utente, voglio una navigazione chiara e non frammentata che rifletta il ruolo centrale dell'agente, così da trovare rapidamente le informazioni e le azioni senza perdermi tra troppe voci di menu.

#### Acceptance Criteria

1. THE ACG SHALL strutturare la navigazione principale in massimo 5 voci operative: "Inbox" (Agent Inbox + Processing Feed), "Documenti" (archivio + Dossier + relazioni), "Scadenze" (calendario + stato notifiche + escalation), "Report" (generazione + storico), e "Agente" (chat avanzata + attività in corso).
2. THE ACG SHALL separare le voci di configurazione (Sorgenti, Regole Escalation, Template Report, Account) in una sezione "Impostazioni" accessibile da icona gear, non nella navigazione principale.
3. THE ACG SHALL mostrare un indicatore persistente dell'attività dell'agente nella navigazione (es. dot animato o micro-badge) che comunica: "inattivo" (grigio), "in elaborazione" (pulsante blu), "richiede attenzione" (badge numerico arancio).
4. THE ACG SHALL posizionare il Chat Agent come elemento accessibile da qualsiasi vista tramite un pannello espandibile dal basso o dalla destra, non come pagina separata che richiede navigazione.
5. WHEN l'utente naviga tra le viste principali, THE Adaptive_Canvas SHALL mantenere il contesto dell'agente visibile (indicatore attività + ultimo messaggio rilevante) senza interruzioni.
6. THE ACG SHALL mostrare un badge con conteggio non-letti sulla voce "Inbox" che somma: AgentInboxItem pending + PendingConfirmation in attesa.

---

### Requirement 17: Adaptive Canvas e Zone Dinamiche

**User Story:** Come utente, voglio che il layout della pagina si adatti automaticamente a quello che sto facendo (revisionare un contratto, gestire scadenze, cercare documenti), così da avere sempre le informazioni rilevanti a portata di mano senza dover aprire pannelli manualmente.

#### Acceptance Criteria

1. THE Adaptive_Canvas SHALL supportare al massimo 3 zone per vista: zona principale (contenuto primario), zona laterale (contesto e dettagli), zona inferiore (chat agent o azioni rapide).
2. WHEN l'utente apre un documento di tipo `contratto`, THE Adaptive_Canvas SHALL attivare la zona laterale con il pannello clausole rischiose e correlazioni cross-document.
3. WHEN l'utente visualizza la lista scadenze, THE Adaptive_Canvas SHALL attivare la zona laterale con lo stato notifiche e le escalation attive per la scadenza selezionata.
4. WHEN l'utente è nella vista Inbox, THE Adaptive_Canvas SHALL attivare la zona laterale con il Processing_Feed e il Quick_View_Panel quando rilevante.
5. THE Adaptive_Canvas SHALL permettere all'utente di chiudere manualmente le zone dinamiche con un gesto (click su X o swipe), e ricordare la preferenza per sessione.
6. THE Adaptive_Canvas SHALL animare le transizioni tra layout con durata massima 200ms, senza jump o reflow visibili del contenuto principale.

---

### Requirement 18: Confirmation Flow Unificato

**User Story:** Come utente, voglio che tutte le richieste di conferma per azioni esterne (invio email, upload Drive, creazione evento) seguano lo stesso pattern visivo e lo stesso livello di dettaglio, così da non dover imparare un'interfaccia diversa per ogni tipo di azione.

#### Acceptance Criteria

1. THE Confirmation_Flow SHALL utilizzare un pattern visivo coerente per tutte le azioni con effetti esterni: modale o pannello con header che indica il tipo di azione, corpo con preview completa dell'effetto, footer con pulsanti "Approva" e "Annulla".
2. THE Confirmation_Flow SHALL includere in ogni preview: la Source_Attribution (da quale documento/scadenza deriva l'azione), il destinatario o la destinazione dell'effetto esterno, e un riepilogo dell'effetto in linguaggio semplice.
3. THE Confirmation_Flow SHALL permettere la modifica inline dei campi editabili (destinatario email, oggetto, corpo testo, cartella Drive) direttamente nella preview senza uscire dal flusso di conferma.
4. WHEN l'utente approva un'azione nel Confirmation_Flow, THE ACG SHALL mostrare un feedback immediato (toast o inline) con lo stato dell'esecuzione: "In corso...", "Completato" (con link al risultato), o "Errore" (con dettaglio e azione suggerita).
5. THE Confirmation_Flow SHALL distinguere visivamente le azioni per risk level: risk 3 (bordo giallo, singola conferma), risk 4 (bordo rosso, doppia conferma con riepilogo esplicito dell'irreversibilità).
6. THE ACG SHALL raggruppare le PendingConfirmation correlate (es. più email di sollecito generate dallo stesso batch) in un'unica vista di conferma batch, con possibilità di approvare/rifiutare singolarmente o in blocco.

---

### Requirement 19: Gestione Errori e Fallback Coerente

**User Story:** Come utente, voglio che il sistema mi comunichi chiaramente cosa è andato storto e cosa posso fare quando si verifica un errore, così da non rimanere bloccato senza sapere come procedere.

#### Acceptance Criteria

1. THE ACG SHALL classificare ogni errore in una delle tre categorie visivamente distinte: "Errore tecnico" (icona ingranaggio rosso — problema di sistema, l'utente non può risolvere), "Dato mancante" (icona documento giallo — serve un input o un documento aggiuntivo), "Azione richiede input umano" (icona utente blu — l'agente ha bisogno di una decisione).
2. WHEN si verifica un errore tecnico (API timeout, servizio non disponibile), THE ACG SHALL mostrare: descrizione non-tecnica del problema, stato "Il team è stato notificato" se applicabile, e pulsante "Riprova" se l'azione è ripetibile.
3. WHEN si verifica un errore di dato mancante (campo obbligatorio assente, documento non trovato), THE ACG SHALL mostrare: quale dato manca, dove trovarlo o come fornirlo, e un'azione diretta per risolvere (es. "Carica documento", "Compila campo").
4. WHEN l'agente richiede input umano (ambiguità, scelta tra opzioni), THE ACG SHALL mostrare: il contesto della decisione, le opzioni disponibili con pro/contro se applicabile, e la conseguenza di ciascuna scelta.
5. THE ACG SHALL loggare ogni errore nell'AuditLog con: timestamp, categoria, contesto (documento/scadenza/azione coinvolta), e stato di risoluzione.
6. IF un'operazione fallisce durante un workflow multi-step, THEN THE ACG SHALL preservare lo stato dei step completati e permettere il retry dal punto di fallimento, senza richiedere di ricominciare dall'inizio.

---

### Requirement 20: Empty State Utili e Onboarding

**User Story:** Come nuovo utente, voglio che ogni sezione vuota mi guidi su cosa fare per attivarla e che il primo accesso sia guidato dall'agente stesso, così da iniziare a usare il sistema rapidamente senza leggere documentazione.

#### Acceptance Criteria

1. THE ACG SHALL mostrare in ogni sezione vuota un empty state che include: illustrazione contestuale, descrizione di cosa la sezione mostrerà una volta attiva, e un'azione primaria per attivarla (es. "Connetti Google Drive" nella sezione Sorgenti, "Carica il primo documento" nella sezione Documenti).
2. THE ACG SHALL guidare il primo accesso con un flusso di onboarding in 4 step gestito dall'agente: (1) Connessione sorgenti (Drive/Gmail/Calendar), (2) Upload o import primo documento, (3) Revisione prima scadenza estratta, (4) Configurazione prima regola di notifica.
3. WHEN l'utente completa ogni step dell'onboarding, THE ACG SHALL mostrare un feedback di progresso e una spiegazione di cosa l'agente farà automaticamente d'ora in poi grazie a quel step completato.
4. THE ACG SHALL permettere di saltare qualsiasi step dell'onboarding e di riprenderlo successivamente dalla sezione Impostazioni.
5. THE ACG SHALL mostrare l'onboarding come conversazione con l'agente (stile chat guidata), non come wizard modale tradizionale, per rinforzare il paradigma agent-centric.
6. WHEN l'utente completa l'onboarding, THE ACG SHALL generare il primo DailyDigest (anche se vuoto o con contenuto minimo) per dimostrare il funzionamento del sistema proattivo.

---

### Requirement 21: Real-Time Layer Trasversale

**User Story:** Come utente, voglio che le informazioni nell'interfaccia si aggiornino in tempo reale (nuovi documenti, stato elaborazione, notifiche) senza dover ricaricare la pagina, così da avere sempre una visione aggiornata della situazione.

#### Acceptance Criteria

1. THE ACG SHALL implementare un layer WebSocket trasversale che emette eventi per: nuovi AgentInboxItem, aggiornamenti stato documenti, nuove notifiche, aggiornamenti stato sorgenti, completamento elaborazioni.
2. WHEN un nuovo AgentInboxItem viene creato, THE ACG SHALL aggiornare la vista Inbox in tempo reale senza refresh, con animazione di inserimento per il nuovo item.
3. WHEN lo stato di una sorgente monitorata cambia (connesso → errore, sincronizzazione completata), THE ACG SHALL aggiornare l'indicatore di stato nella vista Sorgenti e nell'indicatore persistente dell'agente.
4. THE ACG SHALL mostrare un indicatore di connessione WebSocket discreto (es. dot verde/rosso nell'header) che comunica all'utente se il real-time è attivo; IF la connessione WebSocket si interrompe, THEN THE ACG SHALL tentare la riconnessione automatica con backoff esponenziale (1s, 2s, 4s, max 30s) e mostrare un banner "Connessione in corso..." dopo 5 secondi di disconnessione.
5. THE ACG SHALL implementare il real-time come layer opzionale: se il WebSocket non è disponibile, la UI SHALL funzionare con polling a intervalli di 30 secondi come fallback, senza degradazione funzionale.
6. THE ACG SHALL limitare la frequenza degli aggiornamenti real-time a massimo 1 evento per secondo per tipo di risorsa per evitare flooding della UI; eventi multipli nello stesso secondo vengono aggregati in un singolo aggiornamento.

---

### Requirement 22: Zero Hallucination — Source Attribution Universale

**User Story:** Come utente, voglio che ogni dato mostrato dall'agente sia accompagnato dalla sua fonte (documento, pagina, paragrafo) e che i dati incerti siano visivamente distinguibili da quelli certi, così da potermi fidare delle informazioni senza doverle verificare manualmente ogni volta.

#### Acceptance Criteria

1. THE ACG SHALL associare a ogni dato estratto o derivato una Source_Attribution che include: documento sorgente (nome + link), posizione nel documento (pagina, paragrafo o cella), e Confidence_Score.
2. THE ACG SHALL distinguere visivamente tre livelli di certezza per ogni dato mostrato: "Estratto" (icona documento, confidence >= 0.85 — dato letto direttamente dal documento), "Inferito" (icona lampadina, confidence 0.60–0.85 — dato derivato da analisi AI), "Suggerito" (icona punto interrogativo, confidence < 0.60 — ipotesi dell'agente da verificare).
3. WHEN l'utente clicca sulla Source_Attribution di un dato, THE ACG SHALL navigare al documento sorgente evidenziando il passaggio esatto da cui il dato è stato estratto.
4. THE ACG SHALL applicare il sistema di Source_Attribution a tutti i contesti: campi estratti nei documenti, clausole rischiose, correlazioni cross-document, scadenze derivate, e suggerimenti dell'agente nell'Inbox.
5. IF un dato non ha Source_Attribution verificabile (es. suggerimento basato su pattern generali), THEN THE ACG SHALL mostrarlo con un indicatore esplicito "Suggerimento agente — nessuna fonte specifica" e non includerlo nei report esportabili senza conferma esplicita dell'utente.

---

### Requirement 23: Indicatore Attività Agente Persistente

**User Story:** Come utente, voglio sapere in ogni momento cosa l'agente sta facendo o monitorando, così da avere fiducia che il sistema è attivo e sta lavorando per me anche quando non interagisco direttamente.

#### Acceptance Criteria

1. THE ACG SHALL mostrare un indicatore di attività dell'agente persistente e visibile da qualsiasi vista, posizionato nella barra superiore o nella sidebar.
2. THE ACG SHALL comunicare lo stato dell'agente attraverso l'indicatore con: "Monitoraggio attivo" (animazione sottile, sorgenti sincronizzate), "In elaborazione" (animazione evidente, con tooltip che mostra cosa sta processando), "Richiede attenzione" (badge numerico con conteggio azioni in attesa), "Inattivo" (grigio, nessuna sorgente configurata).
3. WHEN l'utente clicca sull'indicatore di attività, THE ACG SHALL espandere un pannello compatto con: lista delle elaborazioni in corso, ultime 5 azioni completate con timestamp, e link rapido alle PendingConfirmation in attesa.
4. THE ACG SHALL aggiornare l'indicatore di attività in tempo reale tramite il WebSocket layer, riflettendo immediatamente l'inizio e la fine di ogni elaborazione.
5. THE ACG SHALL mostrare nell'indicatore un contatore "Documenti processati oggi" come feedback positivo dell'attività autonoma dell'agente.
