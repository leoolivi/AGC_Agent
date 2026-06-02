"""Reset DB — deletes all user data (documents, inbox, tasks, etc.).

Usage: python -m scripts.reset_db
"""
import asyncio

from sqlalchemy import text

from app.config import settings
from app.db.session import build_session_factory


async def reset() -> None:
    factory = build_session_factory(settings.database_url)
    async with factory() as session:
        await session.execute(text("DELETE FROM agent_inbox"))
        await session.execute(text("DELETE FROM pending_confirmations"))
        await session.execute(text("DELETE FROM agent_tasks"))
        await session.execute(text("DELETE FROM email_drafts"))
        await session.execute(text("DELETE FROM notifications"))
        await session.execute(text("DELETE FROM document_chunks"))
        await session.execute(text("DELETE FROM deadlines"))
        await session.execute(text("DELETE FROM documents"))
        await session.execute(text("DELETE FROM audit_log"))
        await session.commit()
        print("✓ DB pulito — tutti i dati utente eliminati")


if __name__ == "__main__":
    asyncio.run(reset())
