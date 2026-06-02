# ACG Setup Guide

Questa guida ti aiuterà a configurare e avviare ACG (Admin & Compliance Guardian) con tutte le funzionalità di Agent Enhancement.

## 📋 Prerequisiti

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+
- Account Google Cloud (per OAuth)

## 🚀 Setup Rapido

### 1. Database Setup

```bash
# Crea database PostgreSQL
createdb acg

# Oppure con Docker
docker run -d \
  --name acg-postgres \
  -e POSTGRES_DB=acg \
  -e POSTGRES_USER=acg \
  -e POSTGRES_PASSWORD=acg \
  -p 5432:5432 \
  postgres:16
```

### 2. Backend Setup

```bash
cd backend

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Genera chiavi di configurazione
python scripts/generate_keys.py

# Copia .env.example e configura
cp .env.example .env
# Modifica .env con le chiavi generate e le tue credenziali

# Esegui migration database
alembic upgrade head

# Avvia server
uvicorn app.main:app --reload
```

Il backend sarà disponibile su `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Installa dipendenze
npm install

# Avvia dev server
npm run dev
```

Il frontend sarà disponibile su `http://localhost:5173`

## 🔐 Configurazione Google OAuth

### 1. Crea Progetto Google Cloud

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuovo progetto o seleziona uno esistente
3. Abilita le seguenti API:
   - Google Drive API
   - Gmail API
   - Google Calendar API

### 2. Configura OAuth Consent Screen

1. Vai su "APIs & Services" > "OAuth consent screen"
2. Seleziona "External" (o "Internal" se hai Google Workspace)
3. Compila i campi richiesti:
   - App name: "ACG - Admin & Compliance Guardian"
   - User support email: tua email
   - Developer contact: tua email
4. Aggiungi gli scope:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/gmail.send`

### 3. Crea Credenziali OAuth

1. Vai su "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Seleziona "Web application"
4. Aggiungi Authorized redirect URIs:
   - `http://localhost:8000/api/v1/oauth/google/callback`
   - `http://localhost:5173/oauth/callback` (per frontend)
5. Copia Client ID e Client Secret nel file `.env`

### 4. Testa OAuth Flow

1. Avvia backend e frontend
2. Vai su Settings > Sorgenti Monitorate
3. Click "Connetti Google Drive"
4. Completa il flusso OAuth
5. Verifica che la connessione sia attiva

## 📦 Dipendenze Principali

### Backend

```txt
fastapi>=0.115.0
sqlalchemy>=2.0.0
alembic>=1.14.0
pydantic>=2.0.0
langchain-core>=0.3.0
langgraph>=0.2.0
structlog>=24.0.0
google-api-python-client>=2.100.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
weasyprint>=60.0
openpyxl>=3.1.0
apscheduler>=3.10.0
hypothesis>=6.100.0
pytest>=8.0.0
```

### Frontend

```json
{
  "react": "^19.0.0",
  "react-dom": "^19.0.0",
  "zustand": "^4.4.0",
  "@tanstack/react-query": "^5.0.0",
  "typescript": "^5.0.0",
  "vite": "^5.0.0"
}
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Test unitari
pytest tests/unit/ -v

# Test property-based
pytest tests/property/ -v

# Test integrazione
pytest tests/integration/ -v

# Tutti i test con coverage
pytest --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Test unitari
npm test

# Test E2E
npm run test:e2e
```

## 🔧 Configurazione Avanzata

### Modalità Dummy (Testing senza Google)

Per testare senza credenziali Google:

```bash
# In .env
USE_DUMMY_ADAPTERS=true
```

Questo userà adapter in-memory che simulano le API Google.

### Storage Alternativo

#### MinIO (S3-compatible)

```bash
# Avvia MinIO con Docker
docker run -d \
  --name acg-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# In .env
FILE_STORAGE_BACKEND=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=acg-documents
```

#### AWS S3

```bash
# In .env
FILE_STORAGE_BACKEND=s3
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### LLM Provider Alternativo

#### Anthropic Claude

```bash
# In .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-key
```

#### OpenAI

```bash
# In .env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
```

#### Ollama (Local)

```bash
# Installa Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Scarica modello
ollama pull llama3

# In .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

## 📊 Monitoraggio

### Logs

I log sono in formato JSON strutturato (structlog):

```bash
# Visualizza log in tempo reale
tail -f logs/acg.log | jq .

# Filtra per livello
tail -f logs/acg.log | jq 'select(.level == "error")'
```

### Metriche

Il sistema espone metriche Prometheus su `/metrics`:

```bash
# Visualizza metriche
curl http://localhost:8000/metrics
```

### Health Check

```bash
# Backend health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db
```

## 🐛 Troubleshooting

### Database Connection Error

```bash
# Verifica che PostgreSQL sia in esecuzione
pg_isready -h localhost -p 5432

# Verifica credenziali in .env
psql -U acg -d acg -h localhost
```

### Google OAuth Error

1. Verifica che le API siano abilitate in Google Cloud Console
2. Verifica che gli scope siano corretti
3. Verifica che il redirect URI sia esatto (incluso http/https)
4. Controlla i log per dettagli: `tail -f logs/acg.log | jq 'select(.event == "oauth")'`

### WebSocket Connection Failed

1. Verifica che il backend sia in esecuzione
2. Controlla CORS settings in `config.py`
3. Verifica JWT token nel browser (DevTools > Application > Local Storage)
4. Prova SSE fallback: `http://localhost:8000/api/v1/events/stream`

### Migration Error

```bash
# Reset database (⚠️ cancella tutti i dati)
alembic downgrade base
alembic upgrade head

# Oppure ricrea database
dropdb acg
createdb acg
alembic upgrade head
```

## 📚 Documentazione Aggiuntiva

- [API Documentation](http://localhost:8000/docs) - Swagger UI
- [Architecture](./docs/architecture.md) - Architettura del sistema
- [User Guide](./docs/user-guide.md) - Guida utente
- [Development](./docs/development.md) - Guida sviluppo

## 🆘 Supporto

Per problemi o domande:
1. Controlla i log: `tail -f logs/acg.log`
2. Verifica la configurazione: `cat .env`
3. Esegui health check: `curl http://localhost:8000/health`
4. Consulta la documentazione API: `http://localhost:8000/docs`

## 🎉 Prossimi Passi

Dopo il setup:

1. **Configura Sorgenti**: Vai su Settings > Sorgenti Monitorate
2. **Carica Documenti**: Testa l'upload di un PDF
3. **Verifica Analisi**: Controlla che le clausole rischiose vengano rilevate
4. **Configura Escalation**: Crea regole di notifica
5. **Genera Report**: Prova a generare un report mensile

Buon lavoro con ACG! 🚀
