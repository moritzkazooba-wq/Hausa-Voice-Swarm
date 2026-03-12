"""SQLAlchemy async engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_engine(url: str, pool_size: int = 10) -> None:
    """Initialize the global async engine and session factory."""
    global _engine, _session_factory
    _engine = create_async_engine(url, pool_size=pool_size, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def dispose_engine() -> None:
    """Dispose the global async engine."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_engine() -> AsyncEngine:
    """Return the global engine (must call init_engine first)."""
    if _engine is None:
        msg = "Engine not initialized — call init_engine() first"
        raise RuntimeError(msg)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global session factory (must call init_engine first)."""
    if _session_factory is None:
        msg = "Session factory not initialized — call init_engine() first"
        raise RuntimeError(msg)
    return _session_factory
