"""Shared test fixtures for hausa-voice-swarm."""

import os
from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest
import redis.asyncio as aioredis


@pytest.fixture
async def mock_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide a fake Redis instance for testing (no real server needed)."""
    server = fakeredis.aioredis.FakeRedis()
    yield server
    await server.aclose()


@pytest.fixture
def cockroachdb_url() -> str:
    """Return CockroachDB URL from env, or skip if not set."""
    url = os.environ.get("COCKROACHDB_URL")
    if not url:
        pytest.skip("COCKROACHDB_URL not set — skipping DB test")
    return url
