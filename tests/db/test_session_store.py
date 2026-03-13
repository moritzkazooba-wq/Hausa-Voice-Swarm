"""Tests for Redis session store."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import redis.asyncio as aioredis
from src.db.session_store import SessionStore
from src.models.session import SessionState


def _make_session(session_id: str = "sess-001") -> SessionState:
    return SessionState(
        session_id=session_id,
        customer_phone="+2348012345678",
        customer_name="Amina Bello",
        language="ha",
        current_intent="balance",
        current_agent="balance",
        started_at=datetime(2026, 3, 13, 12, 0, tzinfo=UTC),
        channel="voice",
    )


@pytest.mark.asyncio
async def test_save_and_get_session(fakeredis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
    """Save a session and retrieve it by ID."""
    store = SessionStore(client=fakeredis_client)
    state = _make_session()
    await store.save(state)

    loaded = await store.get("sess-001")
    assert loaded is not None
    assert loaded.session_id == "sess-001"
    assert loaded.customer_phone == "+2348012345678"
    assert loaded.customer_name == "Amina Bello"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(fakeredis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
    """Getting a non-existent session returns None."""
    store = SessionStore(client=fakeredis_client)
    result = await store.get("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_delete_session(fakeredis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
    """Deleting a session removes it from the store."""
    store = SessionStore(client=fakeredis_client)
    state = _make_session("sess-del")
    await store.save(state)

    await store.delete("sess-del")
    result = await store.get("sess-del")
    assert result is None
