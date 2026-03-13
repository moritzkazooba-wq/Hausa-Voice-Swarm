"""Tests for SQLAlchemy async engine factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from src.config.settings import DatabaseSettings
from src.db.engine import create_engine_from_settings, create_session_factory


def test_create_engine_returns_async_engine() -> None:
    settings = DatabaseSettings()
    engine = create_engine_from_settings(settings)
    assert isinstance(engine, AsyncEngine)


def test_create_session_factory_returns_sessionmaker() -> None:
    engine = create_engine_from_settings()
    factory = create_session_factory(engine)
    assert isinstance(factory, async_sessionmaker)


def test_engine_uses_settings_pool_size() -> None:
    settings = DatabaseSettings(pool_size=5)
    engine = create_engine_from_settings(settings)
    assert engine.pool.size() == 5
