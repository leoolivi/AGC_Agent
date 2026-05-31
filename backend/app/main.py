"""FastAPI application entrypoint."""
from __future__ import annotations

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
from app.api.v1.confirmations import router as confirmations_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.deadlines import router as deadlines_router
from app.api.v1.documents import router as documents_router
from app.api.v1.email_drafts import router as email_drafts_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.oauth_google import router as oauth_google_router
from app.api.v1.settings import router as settings_router

app = FastAPI(title="ACG — Admin & Compliance Guardian", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
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


@app.get("/health")
async def health() -> dict:
    """Health check with DB and storage status."""
    checks: dict = {}
    status = "ok"

    # DB check
    try:
        from app.db.session import build_session_factory
        from app.config import settings
        from sqlalchemy import text
        factory = build_session_factory(settings.database_url)
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        status = "degraded"

    # Storage check
    try:
        from app.api.deps import get_storage
        storage = get_storage()
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "error"
        status = "degraded"

    return {"status": status, "checks": checks}
