# Tech — Stack, Tooling & Coding Standards

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web Framework | FastAPI 0.115 |
| Agent Framework | LangGraph 0.2 + LangChain Core 0.3 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic 1.14 |
| Database | PostgreSQL 16 + pgvector |
| LLM Providers | Anthropic Claude, OpenAI GPT-4o, Google Gemini 1.5 Pro |
| File Storage | Local (dev) / MinIO (self-hosted) / S3 (cloud) |
| Scheduler | APScheduler 3.10 |
| Auth | JWT (python-jose + passlib/bcrypt) |
| HTTP Client | httpx 0.28 |
| Logging | structlog (JSON structured) |
| Validation | Pydantic v2 |
| Frontend (planned) | React 19, TypeScript, Vite, shadcn/ui, TailwindCSS, React Query, Zustand |

## Tooling

| Tool | Config |
|---|---|
| Type checker | `mypy --strict` (Python 3.12 target) |
| Linter/Formatter | `ruff` (line-length 100, rules: E, F, I, UP, B, SIM) |
| Test runner | `pytest` with `pytest-asyncio` (auto mode) |
| Property testing | `hypothesis` |
| Package manager | pip + pyproject.toml (setuptools backend) |

## Commands

```bash
# Lint & format
ruff check backend/ --fix
ruff format backend/

# Type check
mypy backend/app

# Run tests
pytest backend/tests

# Run dev server
uvicorn app.main:app --reload
```

## Coding Standards

- **Type annotations everywhere** — mypy strict mode, no `Any` without justification
- **Async by default** — all I/O-bound operations use `async/await`
- **Protocols over ABCs** — use `typing.Protocol` with `@runtime_checkable` for ports
- **Dataclasses for DTOs** — use `@dataclass` for simple data containers, Pydantic for validated models
- **No hardcoded strings** — prompts in `.md` files, config via `pydantic-settings`
- **Structured logging** — use `structlog` with bound context, never `print()`
- **Imports** — absolute imports from `app.`, sorted by ruff (isort rules)
- **Error handling** — domain exceptions in `core/`, never expose raw adapter errors
- **Test doubles** — `adapters/dummy/` provides in-memory implementations for all ports; tests use these, not mocks

## Dependency Rules

- `core/` → no external imports (only stdlib + pydantic)
- `agent/` → may import from `core/` and `langchain-core`/`langgraph`
- `adapters/` → may import from `core/` and their specific SDK
- `api/` → may import from `core/`, `agent/`, wires adapters via DI
- Never import adapter code inside `core/`
