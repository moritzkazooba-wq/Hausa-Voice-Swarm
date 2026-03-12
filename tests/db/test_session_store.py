"""Tests for Redis session store (uses fakeredis — no real server needed)."""

from datetime import UTC, datetime

import pytest
import redis.asyncio as aioredis
from src.db.session_store import SessionStore
from src.models.session import SessionState


def _make_session(session_id: str = "test-session-001") -> SessionState:
    """Create a sample SessionState for testing."""
    return SessionState(
        session_id=session_id,
        customer_phone="+2348012345678",
        customer_name="Amina Bello",
        language="ha",
        current_intent="check_balance",
        current_agent="balance_agent",
        conversation_turns=[],
        started_at=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
        channel="voice",
        confidence_history=[0.95, 0.88],
    )


@pytest.mark.asyncio
async def test_save_and_get_session(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis, ttl_seconds=300)
    session = _make_session()

    await store.save_session(session)
    loaded = await store.get_session("test-session-001")

    assert loaded is not None
    assert loaded.session_id == "test-session-001"
    assert loaded.customer_phone == "+2348012345678"
    assert loaded.customer_name == "Amina Bello"
    assert loaded.language == "ha"
    assert loaded.confidence_history == [0.95, 0.88]


@pytest.mark.asyncio
async def test_get_nonexistent_session(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis)
    result = await store.get_session("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_delete_session(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis)
    session = _make_session("to-delete")

    await store.save_session(session)
    assert await store.delete_session("to-delete") is True
    assert await store.get_session("to-delete") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_session(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis)
    assert await store.delete_session("never-existed") is False


@pytest.mark.asyncio
async def test_extend_ttl(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis, ttl_seconds=600)
    session = _make_session("ttl-test")

    await store.save_session(session)
    assert await store.extend_ttl("ttl-test") is True

    # Key should still exist
    loaded = await store.get_session("ttl-test")
    assert loaded is not None


@pytest.mark.asyncio
async def test_extend_ttl_nonexistent(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis)
    assert await store.extend_ttl("gone") is False


@pytest.mark.asyncio
async def test_ttl_is_set(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis, ttl_seconds=120)
    session = _make_session("check-ttl")

    await store.save_session(session)
    ttl = await mock_redis.ttl("session:check-ttl")
    assert 0 < ttl <= 120


@pytest.mark.asyncio
async def test_overwrite_session(mock_redis: aioredis.Redis) -> None:
    store = SessionStore(mock_redis)
    session = _make_session("overwrite")
    await store.save_session(session)

    # Update and re-save
    session2 = _make_session("overwrite")
    # model_construct to bypass strict validation for the update
    updated = session2.model_copy(update={"current_intent": "transfer_money"})
    await store.save_session(updated)

    loaded = await store.get_session("overwrite")
    assert loaded is not None
    assert loaded.current_intent == "transfer_money"
