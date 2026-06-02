# ACG - Admin & Compliance Guardian

**Assistente AI proattivo per PMI italiane** che monitora documenti, scadenze e comunicazioni amministrative con analisi intelligente e notifiche progressive.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Funzionalità Principali

### 🤖 Agent-Centric
- **Monitoraggio Proattivo**: L'agente monitora automaticamente Drive, Gmail e Calendar
- **Analisi Intelligente**: Rileva clausole rischiose, correlazioni tra documenti, conflitti
- **Notifiche Progressive**: Sistema di escalation configurabile con HITL

### 📄 Gestione Documenti
- **Upload & Parsing**: Supporto PDF, Excel, CSV con estrazione automatica
- **Classificazione AI**: Riconoscimento automatico tipo documento (contratti, fatture, etc.)
- **Clausole Rischiose**: Analisi contratti con evidenziazione clausole problematiche
- **Source Attribution**: Ogni dato estratto è tracciabile al documento originale

### 🔗 Correlazione Cross-Document
- **Dossier Automatici**: Raggruppa documenti correlati (contratto + fatture + allegati)
- **Rilevamento Conflitti**: Identifica contraddizioni tra documenti
- **Completezza**: Segnala documenti mancanti con certezza "certa" o "probabile"

### 📊 Report & Export
- **Template Predefiniti**: Scadenze mensili, riepilogo fiscale, contratti in scadenza
- **Export PDF/Excel**: Generazione report con dati tracciabili
- **Export Drive/Gmail**: Invio report con HITL e preview

### 🔔 Escalation Intelligente
- **Regole Configurabili**: Definisci tempi, destinatari e canali
- **Multi-Step**: Fino a 5 step con delay crescenti
- **HITL per Email**: Ogni email richiede approvazione esplicita

### 🔄 Real-Time
- **WebSocket**: Aggiornamenti live su processing, notifiche, stato sorgenti
- **Processing Feed**: Vedi in tempo reale i documenti in elaborazione
- **SSE Fallback**: Supporto per ambienti senza WebSocket

## 🚀 Quick Start

### Prerequisiti

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+ (o Docker)
- Account Google Cloud (per OAuth)

### Setup con Docker (Consigliato)

```bash
# Clone repository
git clone https://github.com/your-org/acg.git
cd acg

# Avvia servizi
docker-compose up -d

# Il sistema sarà disponibile su:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
# - API Docs: http://localhost:8000/docs
# - MinIO Console: http://localhost:9001
```

### Setup Manuale

```bash
# 1. Setup completo (installa + migra + inizializza)
make setup

# 2. Genera chiavi di configurazione
make generate-keys

# 3. Configura .env
cp backend/.env.example backend/.env
# Modifica backend/.env con le chiavi generate

# 4. Verifica setup
make verify

# 5. Avvia applicazione
make run
```

Il sistema sarà disponibile su:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

### Login Iniziale

```
Email: admin@acg.local
Password: admin123
```

⚠️ **Cambia la password dopo il primo login!**

## 📖 Documentazione

- [Setup Completo](SETUP.md) - Guida dettagliata setup e configurazione
- [API Documentation](http://localhost:8000/docs) - Swagger UI interattiva
- [Architecture](docs/architecture.md) - Architettura del sistema
- [User Guide](docs/user-guide.md) - Guida utente completa
- [Development](docs/development.md) - Guida per sviluppatori

## 🏗️ Architettura

### Backend (Python + FastAPI)

```
backend/
├── app/
│   ├── core/           # Business logic (ports & adapters)
│   │   ├── domain/     # Pydantic models
│   │   ├── ports/      # Protocol interfaces
│   │   └── services/   # Use cases
│   ├── agent/          # LangGraph AI pipelines
│   │   ├── graphs/     # Workflow graphs
│   │   ├── nodes/      # Graph nodes
│   │   └── prompts/    # System prompts
│   ├── adapters/       # External integrations
│   │   ├── google/     # Drive, Gmail, Calendar
│   │   ├── llm/        # Anthropic, OpenAI, etc.
│   │   ├── report/     # PDF, Excel rendering
│   │   └── realtime/   # WebSocket
│   ├── api/v1/         # FastAPI routers
│   └── db/             # SQLAlchemy models + Alembic
└── tests/
    ├── unit/           # Unit tests
    ├── integration/    # Integration tests
    └── property/       # Property-based tests (Hypothesis)
```

### Frontend (React 19 + TypeScript)

```
frontend/
├── src/
│   ├── components/     # React components
│   │   ├── canvas/     # Adaptive canvas system
│   │   ├── realtime/   # WebSocket components
│   │   ├── reports/    # Report generation
│   │   └── settings/   # Configuration views
│   ├── hooks/          # Custom hooks (useWebSocket, etc.)
│   ├── store/          # Zustand state management
│   ├── api/            # API client (React Query)
│   └── pages/          # Route pages
```

### Stack Tecnologico

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI 0.115, Python 3.12 |
| **AI/Agent** | LangGraph 0.2, LangChain Core 0.3 |
| **Database** | PostgreSQL 16 + pgvector |
| **ORM** | SQLAlchemy 2.0 (async) |
| **LLM** | Anthropic Claude, OpenAI GPT-4o, Gemini |
| **Frontend** | React 19, TypeScript, Vite |
| **UI** | shadcn/ui, TailwindCSS |
| **State** | Zustand, React Query |
| **Real-time** | WebSocket, SSE |
| **Reports** | WeasyPrint (PDF), openpyxl (Excel) |
| **Storage** | Local, MinIO, S3 |
| **Scheduler** | APScheduler |

## 🧪 Testing

```bash
# Tutti i test
make test

# Solo backend
make test-backend

# Solo frontend
make test-frontend

# Con coverage
make test-coverage

# Property-based tests
cd backend && pytest tests/property/ -v
```

### Test Coverage

- **Unit Tests**: 32 test (servizi core)
- **Property-Based Tests**: 10 test (Hypothesis)
- **Integration Tests**: End-to-end flows
- **Total Coverage**: >85%

## 🔧 Comandi Utili

```bash
# Setup e installazione
make setup              # Setup completo
make install            # Installa dipendenze
make migrate            # Esegui migration
make init-db            # Inizializza DB con dati sample

# Sviluppo
make run                # Avvia backend + frontend
make run-backend        # Solo backend
make run-frontend       # Solo frontend
make verify             # Verifica configurazione

# Testing
make test               # Tutti i test
make test-coverage      # Test con coverage
make lint               # Linting
make format             # Formattazione codice

# Database
make reset-db           # Reset database (⚠️ cancella dati)
make logs               # Mostra log applicazione
make health             # Health check

# Docker
make docker-up          # Avvia servizi Docker
make docker-down        # Ferma servizi Docker
make docker-logs        # Log Docker

# Pulizia
make clean              # Pulisci file generati
```

## 🔐 Configurazione Google OAuth

### 1. Crea Progetto Google Cloud

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea nuovo progetto
3. Abilita API: Drive, Gmail, Calendar

### 2. Configura OAuth

1. OAuth consent screen → External
2. Aggiungi scope:
   - `drive.readonly`
   - `gmail.readonly`
   - `calendar.readonly`
   - `calendar.events`
   - `gmail.send`

### 3. Crea Credenziali

1. Credentials → Create OAuth client ID
2. Web application
3. Authorized redirect URIs:
   - `http://localhost:8000/api/v1/oauth/google/callback`
4. Copia Client ID e Secret in `.env`

Vedi [SETUP.md](SETUP.md) per dettagli completi.

## 📊 Monitoraggio

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs

```bash
# Logs strutturati (JSON)
make logs

# Filtra per livello
tail -f backend/logs/acg.log | jq 'select(.level == "error")'
```

### Metriche

```bash
# Prometheus metrics
curl http://localhost:8000/metrics
```

## 🤝 Contribuire

Contributi benvenuti! Per favore:

1. Fork il repository
2. Crea un branch (`git checkout -b feature/amazing-feature`)
3. Commit le modifiche (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

### Linee Guida

- Segui lo stile del codice esistente
- Aggiungi test per nuove funzionalità
- Aggiorna la documentazione
- Usa commit messages descrittivi

## 📝 License

Questo progetto è rilasciato sotto licenza MIT. Vedi [LICENSE](LICENSE) per dettagli.

## 🆘 Supporto

- **Issues**: [GitHub Issues](https://github.com/your-org/acg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/acg/discussions)
- **Email**: support@acg.local

## 🎯 Roadmap

### ✅ Completato (v1.0)
- [x] Monitoraggio passivo Drive/Gmail/Calendar
- [x] Analisi clausole rischiose
- [x] Correlazione cross-document
- [x] Escalation notifiche
- [x] Report PDF/Excel
- [x] Real-time WebSocket
- [x] Adaptive Canvas UI

### 🚧 In Sviluppo (v1.1)
- [ ] Mobile app (React Native)
- [ ] OCR avanzato per documenti scansionati
- [ ] Integrazione Slack/Teams
- [ ] Dashboard analytics avanzata
- [ ] Multi-tenancy

### 🔮 Futuro (v2.0)
- [ ] AI voice assistant
- [ ] Workflow automation builder
- [ ] Integrazione ERP/CRM
- [ ] Compliance checker automatico
- [ ] Blockchain per audit trail

## 🙏 Ringraziamenti

Costruito con:
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [React](https://react.dev/)
- [shadcn/ui](https://ui.shadcn.com/)
- E molte altre librerie open source fantastiche!

---

**Made with ❤️ for Italian SMEs**

🇮🇹 Progettato per le esigenze specifiche delle PMI italiane
