"""Seed script — creates a test user in the database.

Usage: python -m app.db.seed
"""
import asyncio

from sqlalchemy import select

from app.config import settings
from app.core.services.auth_service import hash_password
from app.db.models import User
from app.db.session import build_session_factory

TEST_EMAIL = "admin@acg.local"
TEST_PASSWORD = "admin123"


async def seed() -> None:
    factory = build_session_factory(settings.database_url)
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == TEST_EMAIL))
        if result.scalar_one_or_none():
            print(f"✓ User {TEST_EMAIL} already exists")
            return

        user = User(
            email=TEST_EMAIL,
            hashed_password=hash_password(TEST_PASSWORD),
            name="Admin ACG",
            role="owner",
        )
        session.add(user)
        await session.commit()
        print(f"✓ Created user: {TEST_EMAIL} / {TEST_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
