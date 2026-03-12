"""Redis session store with TTL management."""

import redis.asyncio as aioredis

from src.models.session import SessionState


class SessionStore:
    """Redis-backed session store for active voice/chat sessions."""

    def __init__(self, redis: aioredis.Redis, ttl_seconds: int = 1800) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def get_session(self, session_id: str) -> SessionState | None:
        """Retrieve a session by ID. Returns None if not found or expired."""
        data = await self._redis.get(self._key(session_id))
        if data is None:
            return None
        raw = data if isinstance(data, str) else data.decode()
        return SessionState.model_validate_json(raw)

    async def save_session(self, session: SessionState) -> None:
        """Save or update a session with TTL."""
        await self._redis.set(
            self._key(session.session_id),
            session.model_dump_json(),
            ex=self._ttl,
        )

    async def extend_ttl(self, session_id: str) -> bool:
        """Reset the TTL on an existing session. Returns False if key missing."""
        return bool(await self._redis.expire(self._key(session_id), self._ttl))

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        return bool(await self._redis.delete(self._key(session_id)))
