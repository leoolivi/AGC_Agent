Sei un product designer senior specializzato in SaaS B2B per PMI italiane.
Prima di rispondere, recupera tutto il contesto disponibile su ACG
(Admin & Compliance Guardian) nella conversazione corrente o nei
documenti allegati. Non inventare funzionalità, integrazioni o dettagli
che non siano esplicitamente descritti o ragionevolmente inferibili
dallo stato attuale del prodotto. Se qualcosa è incerto, segnalalo
esplicitamente invece di assumere.

---

## Contesto prodotto

ACG è un agente AI per la gestione di documenti amministrativi
aziendali. Sidebar attuale: Dashboard, Documenti, Scadenze, Chat Agent,
Conferme, Email, Audit Log, Impostazioni.

La funzionalità core è un Chat Agent che, in linguaggio naturale,
analizza documenti, estrae scadenze, crea reminder, genera bozze email
di sollecito e notifiche interne. Stack di integrazione attuale:
Google Drive e Gmail (parziale).

---

## Principi trasversali di progettazione

Questi principi devono permeare ogni decisione di feature e UX,
non essere aggiunti a posteriori.

### Agent-centric UI
L'agente non è una tab — è il centro gravitazionale dell'interfaccia.
La UI deve comunicare che l'agente è sempre attivo, sempre presente,
e che l'utente sta collaborando con lui, non usando uno strumento.
Progetta un design system che renda questa relazione visiva e palpabile:
presenza persistente dell'agente, indicatori di attività in tempo reale,
feedback continuo su cosa sta facendo o monitorando.

### Adaptive canvas
Le viste principali non sono statiche. Il canvas cambia in base
all'attività corrente dell'utente: se sta revisionando un contratto,
il pannello contestuale mostra clausole e correlazioni; se sta
guardando le scadenze della settimana, mostra lo stato notifiche e
le azioni pendenti. I cambiamenti devono essere fluidi e prevedibili,
non sorprendenti. Non esagerare: al massimo 2-3 zone dinamiche per
vista, il resto stabile.

### HITL — Human in the Loop come design principle
Ogni azione che ha effetti esterni (invio email, creazione evento
calendario, modifica documento Drive, creazione scadenza) richiede
una conferma esplicita dell'utente. Il design del confirmation flow
deve essere frictionless ma inequivocabile: non un semplice "Sei
sicuro?" ma una preview chiara di cosa sta per succedere e a chi.
L'agente propone, l'utente decide. Progetta questo come sistema
coerente in tutta la UI, non caso per caso.

### Zero hallucination UI
La UI deve rendere visivamente distinguibile cosa è stato estratto
da un documento (con source link e confidence) da cosa è stato
inferito o suggerito dall'agente. Nessun dato deve apparire senza
attribuzione. Progetta un sistema di "evidenza" — ogni informazione
mostra da dove viene. Dove il sistema è incerto, lo comunica
esplicitamente con un indicatore visivo, non tace o inventa.

### Real-time
Notifiche, stato processing, aggiornamenti da Drive/Gmail/Calendar
sono live. Progetta il sistema di real-time come layer trasversale:
indicatori di attività dell'agente sempre visibili, feed di eventi
in tempo reale, stato sincronizzazione delle sorgenti. Senza
trasformare la UI in un dashboard di monitoring.

---

## Asse 1 — Ingest passivo automatico

L'agente monitora Gmail e Google Drive in background. Ogni documento
nuovo viene processato automaticamente: scadenze estratte, inserite
nel sistema, senza azione dell'utente.

Progetta:
- UI "Sorgenti monitorate": configurazione cartelle Drive, label Gmail,
  frequenza polling, con stato connessione live
- Feed "In arrivo" con stato processing real-time (in analisi /
  completato / richiede attenzione umana)
- Come il feed si integra nel canvas principale senza creare rumore
- Integrazione con Google Calendar: rilevamento automatico di eventi
  rilevanti (scadenze contrattuali, appuntamenti con fornitori) da
  proporre come scadenze tracciate in ACG — con HITL prima di importare

---

## Asse 2 — Rilevamento clausole rischiose

Quando viene caricato un contratto, l'agente evidenzia proattivamente
rinnovi automatici, penali, limitazioni responsabilità, clausole di
recesso. Ogni evidenziazione deve essere attribuita al testo sorgente
con citazione precisa — nessuna clausola flaggata senza source.

Progetta:
- Vista "Analisi contratto" con highlight visivo per categoria di rischio,
  ogni highlight linkato alla pagina/paragrafo sorgente
- Pannello laterale con spiegazione plain-language di ogni clausola,
  con confidence indicator quando l'interpretazione è inferita
- Integrazione nel canvas Documenti: quando apri un contratto,
  il canvas adatta automaticamente il layout per mostrare l'analisi

---

## Asse 3 — Cross-document intelligence

L'agente correla documenti: fattura vs contratto quadro, allegati
mancanti, contraddizioni tra versioni. Le correlazioni devono essere
basate su evidenza documentale esplicita, non su inferenze opache.

Progetta:
- Vista "Relazioni" con grafo leggero o lista strutturata dei link
  tra documenti, con indicazione della fonte di ogni correlazione
- Conflict warning con preview side-by-side dei passaggi in conflitto,
  entrambi citati
- Sistema "Dossier incompleto": cosa manca per completare un fascicolo,
  con distinzione tra "mancante con certezza" e "probabilmente mancante"

---

## Asse 4 — Escalation intelligente notifiche

Notifiche progressive: se una scadenza non viene confermata entro X ore,
l'escalation cambia destinatario o canale. Invio email reale tramite
Gmail — sempre con HITL prima dell'invio effettivo.

Progetta:
- UI configurazione regole escalation per tipo di scadenza,
  con anteprima del flow prima di salvare
- Vista "Stato notifiche" live: chi ha ricevuto cosa, se ha aperto,
  se ha risposto — dati reali da Gmail, non simulati
- Gestione fallback visibile: email non trovata, destinatario assente,
  con azione suggerita e richiesta conferma prima di procedere

---

## Asse 5 — Report esportabile

Genera PDF/Excel con scadenze del periodo per commercialista o
management. I dati nel report devono essere esclusivamente quelli
presenti nel sistema, tracciabili a documenti reali.

Progetta:
- UI "Report" con selezione periodo, filtri, anteprima live
- Template predefiniti (mensile, trimestrale fisco, contratti in
  scadenza) configurabili
- Export one-click verso Drive (con scelta cartella) e invio diretto
  via Gmail — entrambi con HITL confirmation prima di eseguire
- Generazione documento direttamente in Google Drive nella cartella
  configurata, con link diretto al file creato

---

## Asse 6 — Quick view G Suite embedded

Non un'integrazione completa: una finestra contestuale per decidere
cosa importare in ACG senza uscire dall'app.

Progetta:
- Pannello "Drive" con file recenti e cartelle, checkbox per import
  selettivo — l'import avviene solo dopo conferma esplicita
- Pannello "Calendar" con eventi 30 giorni, flag per trasformarli in
  scadenze tracciate — con anteprima di come verranno importati
- Posizionamento nella UI: integrato nel canvas contestuale quando
  rilevante, non come tab separata permanente

---

## Asse 7 — Revisione navigazione e architettura UI

La sidebar attuale va rivalutata alla luce dell'approccio agent-centric
e delle nuove feature.

Progetta:
- Nuova architettura di navigazione che riduce la frammentazione:
  identifica cosa accorpare, cosa elevare, cosa spostare in settings
- Gerarchia chiara tra "viste operative quotidiane" e "configurazione"
- Posizione e peso visivo del Chat Agent nel nuovo layout:
  se è il centro, deve sembrarlo strutturalmente
- Come le zone dinamiche del canvas si raccordano con la navigazione
  principale senza conflitti

---

## Asse 8 — Solidità UX trasversale

Progetta come sistema coerente, non feature per feature:
- Confirmation flow unificato per tutte le azioni esterne
  (email, calendar, Drive): stesso pattern visivo, stesso livello
  di dettaglio nella preview, sempre con source delle informazioni
- Gestione errori e fallback coerente in tutta la UI, con distinzione
  tra "errore tecnico", "dato mancante" e "azione richiede input umano"
- Empty state utili: ogni sezione mostra cosa fare per attivarla,
  non solo "nessun dato presente"
- Onboarding primo accesso: connessione sorgenti → primo documento →
  prima scadenza → prima notifica, guidato dall'agente stesso

---

## Output atteso

Per ogni asse:
1. Feature concrete con nome e descrizione (2 righe max)
2. Comportamento UI: cosa vede l'utente, come interagisce,
   come cambia il canvas se applicabile
3. Dipendenze tecniche e integrazioni necessarie (solo quelle
   effettivamente richieste dalla feature)
4. Priority score: P0 / P1 / P2 basato su impatto percepito dal cliente

Alla fine: roadmap in 3 fasi (MVP differenziante, Consolidamento,
Espansione) con feature assegnate alle fasi e motivazione.

Sii concreto. Ogni feature deve essere abbastanza specifica da
entrare in un ticket di sviluppo. Se qualcosa è ambiguo o richiede
decisioni architetturali che non puoi fare senza più contesto,
segnalalo esplicitamente invece di inventare una soluzione.