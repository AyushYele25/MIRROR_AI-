"""Async SQLAlchemy engine and session factory.

Uses asyncpg driver for PostgreSQL. The session dependency is designed for
FastAPI's dependency injection — yields a session and auto-closes it.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")

engine_kwargs = {
    "echo": settings.app_debug and not settings.is_production,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    })
else:
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
    })

engine = create_async_engine(settings.database_url, **engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
