# Structure — Directory Layout & Conventions

## Monorepo Layout

```
acg/
├── backend/                    # Python backend (FastAPI + LangGraph)
│   ├── app/
│   │   ├── core/               # Pure business logic, zero external deps
│   │   │   ├── domain/         # Entities & value objects (Pydantic v2)
│   │   │   ├── ports/          # Protocol definitions (interfaces)
│   │   │   └── services/       # Use cases
│   │   ├── agent/
│   │   │   ├── graphs/         # LangGraph graphs (Triage, Workflow, DailyDigest)
│   │   │   ├── nodes/          # Individual LangGraph nodes
│   │   │   ├── tools/          # Tool registry
│   │   │   ├── risk/           # RiskEngine + rules.yaml
│   │   │   ├── workflows/      # WorkflowTemplateRegistry + templates
│   │   │   ├── prompts/        # System prompts as .md files (never hardcoded)
│   │   │   └── guardrails/     # constitution.md, blacklist.yaml, GuardrailLayer
│   │   ├── adapters/           # Concrete implementations of ports
│   │   │   ├── storage/        # local, minio, s3
│   │   │   ├── llm/            # anthropic, openai, gemini, fallback_chain
│   │   │   ├── parsers/        # pdf_parser, spreadsheet_parser
│   │   │   ├── email/          # smtp_adapter
│   │   │   ├── calendar/       # google_calendar_adapter (deferred)
│   │   │   ├── vector/         # pgvector_adapter
│   │   │   └── notifier/       # inapp_notifier, email_notifier
│   │   ├── api/v1/             # FastAPI routers
│   │   └── db/                 # SQLAlchemy models + Alembic migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/                   # React 19 + TypeScript + Vite (planned)
└── .kiro/
    ├── steering/               # Project context for AI agents
    └── specs/                  # Feature specifications
```

## Architecture: Hexagonal (Ports & Adapters)

- `core/` contains pure business logic with **no imports from adapters or frameworks**
- Every external dependency is accessed via a `typing.Protocol` in `core/ports/`
- Adapters implement protocols and live in `adapters/`
- Wiring happens in `app/api/deps.py` via environment variables
- `adapters/dummy/` provides in-memory test doubles for all ports

## Naming Conventions

- Ports: `{Capability}Port` (e.g., `FileStoragePort`, `LLMProviderPort`)
- Adapters: `{Provider}{Capability}Adapter` (e.g., `AnthropicLLMAdapter`)
- Services: `{Domain}Service` (e.g., `DocumentService`, `DeadlineService`)
- Graphs: `{Purpose}Graph` (e.g., `TriageGraph`, `WorkflowGraph`)
- API routers: one file per resource in `api/v1/`

## Key Rules

- `core/` must never import from `adapters/`, `api/`, or `db/`
- Prompts live as `.md` files in `agent/prompts/`, never hardcoded in Python
- Each adapter module has an `__init__.py` that re-exports the adapter class
- Dummy adapters mirror the real adapter interface for testing without external services
