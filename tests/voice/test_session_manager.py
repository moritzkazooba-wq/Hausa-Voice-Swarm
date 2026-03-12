"""Tests for SessionManager lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import redis.asyncio as aioredis
from src.models.session import SessionState
from src.voice.session_manager import SessionManager

# ── Session start ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_creates_session_in_redis(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_start creates a SessionState and stores it in Redis."""
    mgr = SessionManager(redis=mock_redis)
    session = await mgr.on_session_start(
        "sess-1", "+2348012345678",
    )

    assert isinstance(session, SessionState)
    assert session.session_id == "sess-1"
    assert session.customer_phone == "+2348012345678"
    assert session.customer_name == "Amina Bello"
    assert session.language == "ha"
    assert session.channel == "voice"
    assert session.conversation_turns == []


@pytest.mark.asyncio
async def test_start_unknown_customer(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_start uses 'Unknown' for unrecognised phone numbers."""
    mgr = SessionManager(redis=mock_redis)
    session = await mgr.on_session_start(
        "sess-2", "+2349999999999",
    )

    assert session.customer_name == "Unknown"


@pytest.mark.asyncio
async def test_start_increments_gauge(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_start adds session to active set."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-3", "+2348012345678")

    assert "sess-3" in mgr.active_sessions
    assert mgr.active_count == 1


@pytest.mark.asyncio
async def test_start_publishes_event(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_start publishes SessionStartedEvent via producer."""
    producer = AsyncMock()
    mgr = SessionManager(redis=mock_redis, producer=producer)
    await mgr.on_session_start(
        "sess-4", "+2348012345678",
    )

    producer.publish.assert_awaited_once()
    event = producer.publish.call_args[0][0]
    assert event.session_id == "sess-4"
    assert event.customer_phone == "+2348012345678"


@pytest.mark.asyncio
async def test_start_restores_existing_session(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_start restores an existing session from Redis."""
    mgr = SessionManager(redis=mock_redis)

    # Create initial session
    original = await mgr.on_session_start(
        "sess-5", "+2348012345678",
    )

    # Add a turn to track state
    await mgr.on_turn_complete(
        "sess-5", "Hello", "Hi there!", intent="greeting",
    )

    # "Restore" same session
    restored = await mgr.on_session_start(
        "sess-5", "+2348012345678",
    )

    assert restored.session_id == original.session_id
    assert len(restored.conversation_turns) == 2


# ── Turn tracking ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_turn_complete_appends_messages(
    mock_redis: aioredis.Redis,
) -> None:
    """on_turn_complete adds user and assistant messages."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-6", "+2348012345678")

    updated = await mgr.on_turn_complete(
        "sess-6",
        "Check my balance",
        "Your balance is 15,000 NGN.",
        intent="balance",
        confidence=0.95,
        agent_name="balance_agent",
    )

    assert updated is not None
    assert len(updated.conversation_turns) == 2
    assert updated.conversation_turns[0].role == "user"
    assert updated.conversation_turns[0].content == "Check my balance"
    assert updated.conversation_turns[1].role == "assistant"
    assert updated.conversation_turns[1].agent_name == "balance_agent"
    assert updated.current_intent == "balance"
    assert updated.confidence_history == [0.95]


@pytest.mark.asyncio
async def test_turn_complete_no_session_returns_none(
    mock_redis: aioredis.Redis,
) -> None:
    """on_turn_complete returns None for unknown session."""
    mgr = SessionManager(redis=mock_redis)
    result = await mgr.on_turn_complete(
        "nonexistent", "hello", "world",
    )

    assert result is None


@pytest.mark.asyncio
async def test_turn_complete_extends_ttl(
    mock_redis: aioredis.Redis,
) -> None:
    """on_turn_complete re-saves session which extends Redis TTL."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-7", "+2348012345678")
    await mgr.on_turn_complete(
        "sess-7", "Hi", "Hello!",
    )

    # Verify the session is still in Redis
    data = await mock_redis.get("session:sess-7")
    assert data is not None


# ── Session end ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_end_removes_from_redis(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_end removes session from Redis."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-8", "+2348012345678")
    await mgr.on_session_end("sess-8", "resolved")

    data = await mock_redis.get("session:sess-8")
    assert data is None
    assert "sess-8" not in mgr.active_sessions


@pytest.mark.asyncio
async def test_end_publishes_event(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_end publishes SessionEndedEvent."""
    producer = AsyncMock()
    mgr = SessionManager(redis=mock_redis, producer=producer)
    await mgr.on_session_start("sess-9", "+2348012345678")

    # Reset mock to clear start event
    producer.publish.reset_mock()
    await mgr.on_session_end("sess-9", "hangup")

    producer.publish.assert_awaited_once()
    event = producer.publish.call_args[0][0]
    assert event.session_id == "sess-9"
    assert event.reason == "hangup"


@pytest.mark.asyncio
async def test_end_decrements_active_count(
    mock_redis: aioredis.Redis,
) -> None:
    """on_session_end removes session from active set."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-10", "+2348012345678")
    assert mgr.active_count == 1

    await mgr.on_session_end("sess-10", "resolved")
    assert mgr.active_count == 0


# ── Shutdown persistence ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_persist_for_shutdown_extends_ttl(
    mock_redis: aioredis.Redis,
) -> None:
    """persist_for_shutdown sets 1-hour TTL on session."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-11", "+2348012345678")

    result = await mgr.persist_for_shutdown("sess-11")
    assert result is True

    ttl = await mock_redis.ttl("session:sess-11")
    assert ttl == 3600


@pytest.mark.asyncio
async def test_persist_for_shutdown_missing_session(
    mock_redis: aioredis.Redis,
) -> None:
    """persist_for_shutdown returns False for missing session."""
    mgr = SessionManager(redis=mock_redis)
    result = await mgr.persist_for_shutdown("nonexistent")
    assert result is False
