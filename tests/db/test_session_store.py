"""Tests for the Redis session store."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.db.session_store import RedisSessionStore
from src.models.session import AgentMessage, SessionState


def _make_session(session_id: str = "test-session-001") -> SessionState:
    """Create a minimal SessionState for testing."""
    return SessionState(
        session_id=session_id,
        customer_phone="+2348012345678",
        customer_name="Amina Bello",
        language="ha",
        current_intent="balance",
        current_agent="balance",
        started_at=datetime(2026, 3, 13, 9, 0, tzinfo=UTC),
        channel="voice",
    )


@pytest.mark.asyncio
async def test_save_and_get(fakeredis_client) -> None:  # type: ignore[no-untyped-def]
    store = RedisSessionStore(fakeredis_client, ttl=60)
    session = _make_session()
    await store.save(session)

    loaded = await store.get("test-session-001")
    assert loaded is not None
    assert loaded.session_id == "test-session-001"
    assert loaded.customer_phone == "+2348012345678"
    assert loaded.language == "ha"


@pytest.mark.asyncio
async def test_get_nonexistent(fakeredis_client) -> None:  # type: ignore[no-untyped-def]
    store = RedisSessionStore(fakeredis_client)
    result = await store.get("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_delete(fakeredis_client) -> None:  # type: ignore[no-untyped-def]
    store = RedisSessionStore(fakeredis_client)
    session = _make_session("del-session")
    await store.save(session)
    assert await store.exists("del-session") is True

    await store.delete("del-session")
    assert await store.exists("del-session") is False


@pytest.mark.asyncio
async def test_exists(fakeredis_client) -> None:  # type: ignore[no-untyped-def]
    store = RedisSessionStore(fakeredis_client)
    assert await store.exists("nope") is False

    await store.save(_make_session("exists-test"))
    assert await store.exists("exists-test") is True


@pytest.mark.asyncio
async def test_roundtrip_with_messages(fakeredis_client) -> None:  # type: ignore[no-untyped-def]
    store = RedisSessionStore(fakeredis_client)
    session = _make_session("msg-session")
    session.conversation_turns.append(
        AgentMessage(
            role="user",
            content="What is my balance?",
            timestamp=datetime(2026, 3, 13, 9, 1, tzinfo=UTC),
            agent_name="balance",
        )
    )
    session.confidence_history.append(0.85)

    await store.save(session)
    loaded = await store.get("msg-session")
    assert loaded is not None
    assert len(loaded.conversation_turns) == 1
    assert loaded.conversation_turns[0].content == "What is my balance?"
    assert loaded.confidence_history == [0.85]


@pytest.mark.asyncio
async def test_overwrite_session(fakeredis_client) -> None:  # type: ignore[no-untyped-def]
    store = RedisSessionStore(fakeredis_client)
    session = _make_session("overwrite")
    await store.save(session)

    session.current_intent = "transfer"
    await store.save(session)

    loaded = await store.get("overwrite")
    assert loaded is not None
    assert loaded.current_intent == "transfer"
