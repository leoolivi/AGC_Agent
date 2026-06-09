"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# LangSmith tracing
if settings.langsmith_enabled and settings.langsmith_api_key:
    import os
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

from app.api.v1.agent import router as agent_router
from app.api.v1.audit import router as audit_router
from app.api.v1.chat import router as chat_router
from app.api.v1.auth import router as auth_router
from app.api.v1.clauses import router as clauses_router
from app.api.v1.confirmations import router as confirmations_router
from app.api.v1.correlations import router as correlations_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.deadlines import router as deadlines_router
from app.api.v1.documents import router as documents_router
from app.api.v1.folders import router as folders_router
from app.api.v1.dossiers import router as dossiers_router
from app.api.v1.email_drafts import router as email_drafts_router
from app.api.v1.escalation_rules import router as escalation_rules_router
from app.api.v1.escalation_rules import status_router as escalation_status_router
from app.api.v1.events import router as events_router
from app.api.v1.google_drive import router as google_drive_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.oauth_google import router as oauth_google_router
from app.api.v1.reports import router as reports_router
from app.api.v1.settings import router as settings_router
from app.api.v1.sources import router as sources_router
from app.api.v1.websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    try:
        from app.adapters.scheduler.source_poll_scheduler import get_source_poll_scheduler
        scheduler = get_source_poll_scheduler()
        scheduler.start()
        await scheduler.register_all_active_sources()
    except Exception:
        pass
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="ACG — Admin & Compliance Guardian", version="0.1.0", lifespan=lifespan)

_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(folders_router, prefix="/api/v1")
app.include_router(confirmations_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(inbox_router, prefix="/api/v1")
app.include_router(deadlines_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(email_drafts_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(oauth_google_router, prefix="/api/v1")
app.include_router(google_drive_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(clauses_router, prefix="/api/v1")
app.include_router(correlations_router, prefix="/api/v1")
app.include_router(dossiers_router, prefix="/api/v1")
app.include_router(escalation_rules_router, prefix="/api/v1")
app.include_router(escalation_status_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(websocket_router)


@app.get("/health")
async def health() -> dict:
    """Health check with DB and storage status."""
    checks: dict = {}
    status = "ok"

    try:
        from app.db.session import build_session_factory
        from sqlalchemy import text
        factory = build_session_factory(settings.database_url)
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        status = "degraded"

    try:
        from app.api.deps import get_storage
        get_storage()
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "error"
        status = "degraded"

    return {"status": status, "checks": checks}
