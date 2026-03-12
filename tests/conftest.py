"""Shared test fixtures — layered hierarchy for hausa-voice-swarm.

Layer 1 (Base): fakeredis_client, db_session
Layer 2 (Service): mock_kafka_producer, mock_graphql_client
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
import redis.asyncio as aioredis
import src.api.app as app_module
from httpx import ASGITransport, AsyncClient
from src.api.app import create_app
from src.events.producer import KafkaEventProducer

# ---------------------------------------------------------------------------
# Layer 1 — Base fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def fakeredis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide a fake Redis instance for testing (no real server needed)."""
    server = fakeredis.aioredis.FakeRedis()
    yield server
    await server.aclose()


@pytest.fixture
def db_session() -> None:
    """Async SQLAlchemy session — skips when COCKROACHDB_URL is not set.

    Placeholder until SQLAlchemy ORM models are added.  Once engine.py
    provides ``create_async_engine``, this fixture will yield a real
    ``AsyncSession`` bound to a test transaction that rolls back.
    """
    url = os.environ.get("COCKROACHDB_URL")
    if not url:
        pytest.skip("COCKROACHDB_URL not set — skipping DB test")


# ---------------------------------------------------------------------------
# Layer 2 — Service fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_kafka_producer() -> KafkaEventProducer:
    """KafkaEventProducer with ``publish`` mocked to record published events.

    Access recorded events via ``producer.publish.call_args_list``.
    """
    producer = KafkaEventProducer()
    producer.publish = AsyncMock()  # type: ignore[method-assign]
    return producer


@pytest.fixture
async def mock_graphql_client() -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client wired to the FastAPI app for GraphQL testing.

    Supports all standard queries (balance, transactions) and mutations.
    """
    app = create_app()
    app_module._ready = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app_module._ready = False
