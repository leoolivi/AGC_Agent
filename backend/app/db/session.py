"""SQLAlchemy async engine and session factory."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):  # noqa: ANN201
    return create_async_engine(database_url, echo=False)


def build_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = build_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)
