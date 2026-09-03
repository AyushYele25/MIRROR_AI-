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

import re

def _normalize_database_url(raw_url: str) -> str:
    """Normalize database connection URLs for asyncpg compatibility."""
    url = raw_url.strip()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "asyncpg" in url:
        had_ssl = "sslmode=" in url or "neon.tech" in url or "ssl=require" in url
        # Strip libpq-specific parameters unsupported by asyncpg
        url = re.sub(r"[?&]sslmode=[^&]+", "", url)
        url = re.sub(r"[?&]channel_binding=[^&]+", "", url)
        if had_ssl and "ssl=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}ssl=require"
    return url


db_url = _normalize_database_url(settings.database_url)
is_sqlite = db_url.startswith("sqlite")

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

engine = create_async_engine(db_url, **engine_kwargs)

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
