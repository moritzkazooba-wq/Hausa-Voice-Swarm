"""SQLAlchemy async engine and session factory for CockroachDB.

Provides ``create_engine_from_settings`` to build an ``AsyncEngine`` and
``create_session_factory`` to produce ``AsyncSession`` instances bound to it.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import DatabaseSettings


def create_engine_from_settings(
    settings: DatabaseSettings | None = None,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine from application settings.

    Uses the ``COCKROACHDB_URL`` connection string (asyncpg driver).
    """
    if settings is None:
        settings = DatabaseSettings()
    return create_async_engine(
        settings.cockroachdb_url,
        pool_size=settings.pool_size,
        echo=False,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)
