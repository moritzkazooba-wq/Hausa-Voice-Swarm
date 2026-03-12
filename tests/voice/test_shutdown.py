"""Tests for GracefulShutdown handler."""

from __future__ import annotations

import asyncio

import pytest
import redis.asyncio as aioredis
from src.voice.session_manager import SessionManager
from src.voice.shutdown import GracefulShutdown


@pytest.mark.asyncio
async def test_shutdown_initial_state(
    mock_redis: aioredis.Redis,
) -> None:
    """GracefulShutdown starts in non-shutdown state."""
    mgr = SessionManager(redis=mock_redis)
    shutdown = GracefulShutdown(mgr)

    assert shutdown.is_shutting_down is False
    assert not shutdown.shutdown_complete.is_set()


@pytest.mark.asyncio
async def test_shutdown_drains_when_no_sessions(
    mock_redis: aioredis.Redis,
) -> None:
    """Shutdown completes immediately when no active sessions."""
    mgr = SessionManager(redis=mock_redis)
    shutdown = GracefulShutdown(mgr)

    # Simulate drain directly
    await shutdown._drain_and_persist()

    assert shutdown.shutdown_complete.is_set()


@pytest.mark.asyncio
async def test_shutdown_persists_remaining_sessions(
    mock_redis: aioredis.Redis,
) -> None:
    """Shutdown persists remaining sessions with extended TTL."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-shutdown-1", "+2348012345678")

    shutdown = GracefulShutdown(mgr, max_drain_seconds=0.1)
    shutdown._shutting_down = True

    # Drain times out quickly, then persists remaining
    await shutdown._drain_and_persist()

    assert shutdown.shutdown_complete.is_set()

    # Session should still exist in Redis with extended TTL
    ttl = await mock_redis.ttl("session:sess-shutdown-1")
    assert ttl == 3600


@pytest.mark.asyncio
async def test_shutdown_waits_for_sessions_to_drain(
    mock_redis: aioredis.Redis,
) -> None:
    """Shutdown waits for sessions to end before completing."""
    mgr = SessionManager(redis=mock_redis)
    await mgr.on_session_start("sess-drain-1", "+2348012345678")

    shutdown = GracefulShutdown(mgr)

    # End the session after a short delay
    async def end_soon() -> None:
        await asyncio.sleep(0.1)
        await mgr.on_session_end("sess-drain-1", "resolved")

    task = asyncio.create_task(end_soon())
    await shutdown._drain_and_persist()
    await task

    assert shutdown.shutdown_complete.is_set()
    assert mgr.active_count == 0


@pytest.mark.asyncio
async def test_shutdown_wait_for_shutdown(
    mock_redis: aioredis.Redis,
) -> None:
    """wait_for_shutdown blocks until shutdown_complete is set."""
    mgr = SessionManager(redis=mock_redis)
    shutdown = GracefulShutdown(mgr)

    # Set the event immediately
    shutdown.shutdown_complete.set()
    # Should return without blocking
    await asyncio.wait_for(
        shutdown.wait_for_shutdown(), timeout=1.0,
    )
