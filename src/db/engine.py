"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import DatabaseSettings

_settings = DatabaseSettings()

engine = create_async_engine(
    _settings.cockroachdb_url,
    pool_size=_settings.pool_size,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session (for dependency injection)."""
    async with async_session_factory() as session:
        yield session
