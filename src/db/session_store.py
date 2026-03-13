"""Redis session store — caches active call state with TTL."""

from __future__ import annotations

import redis.asyncio as aioredis

from src.config.settings import RedisSettings
from src.models.session import SessionState


class SessionStore:
    """Redis-backed session cache with configurable TTL.

    Keys: ``session:{session_id}`` → JSON-serialized ``SessionState``.
    """

    def __init__(
        self,
        client: aioredis.Redis | None = None,
        settings: RedisSettings | None = None,
    ) -> None:
        self._settings = settings or RedisSettings()
        self._client = client  # injected in tests (fakeredis)

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._settings.redis_url)
        return self._client

    async def get(self, session_id: str) -> SessionState | None:
        """Retrieve session state by ID, or ``None`` if not found / expired."""
        client = await self._get_client()
        data: bytes | None = await client.get(f"session:{session_id}")
        if data is None:
            return None
        return SessionState.model_validate_json(data)

    async def save(self, state: SessionState) -> None:
        """Persist session state with TTL."""
        client = await self._get_client()
        await client.set(
            f"session:{state.session_id}",
            state.model_dump_json(),
            ex=self._settings.session_ttl_seconds,
        )

    async def delete(self, session_id: str) -> None:
        """Remove a session from the cache."""
        client = await self._get_client()
        await client.delete(f"session:{session_id}")

    async def close(self) -> None:
        """Shut down the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
