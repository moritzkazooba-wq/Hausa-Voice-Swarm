"""Redis session store with TTL-based expiry.

Stores active call state as JSON-serialized ``SessionState`` Pydantic models
with a configurable TTL (default 30 minutes).
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis

from src.models.session import SessionState

logger = structlog.get_logger()

# Key prefix for session entries
_KEY_PREFIX = "session:"


class RedisSessionStore:
    """CRUD operations for session state in Redis.

    Parameters
    ----------
    redis:
        Async Redis client (real or fakeredis for tests).
    ttl:
        Time-to-live in seconds for each session key (default 1800 = 30 min).
    """

    def __init__(self, redis: Redis, ttl: int = 1800) -> None:
        self._redis = redis
        self._ttl = ttl

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def get(self, session_id: str) -> SessionState | None:
        """Retrieve a session by ID. Returns None if not found or expired."""
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            return None
        data = raw if isinstance(raw, str) else raw.decode("utf-8")
        return SessionState.model_validate_json(data)

    async def save(self, state: SessionState) -> None:
        """Persist a session with TTL refresh."""
        await self._redis.set(
            self._key(state.session_id),
            state.model_dump_json(),
            ex=self._ttl,
        )
        await logger.adebug(
            "session_saved",
            session_id=state.session_id,
            ttl=self._ttl,
        )

    async def delete(self, session_id: str) -> None:
        """Remove a session from the store."""
        await self._redis.delete(self._key(session_id))

    async def exists(self, session_id: str) -> bool:
        """Check whether a session exists (and hasn't expired)."""
        return bool(await self._redis.exists(self._key(session_id)))
