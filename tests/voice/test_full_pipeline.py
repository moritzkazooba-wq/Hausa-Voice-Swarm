"""Integration tests: full call lifecycle and session restart.

Tests the complete flow: connect → balance check → goodbye,
and session restart: start → turn → shutdown → new instance → restore.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as aioredis
from src.models.transaction import ActionResult
from src.voice.session_manager import SessionManager


@pytest.mark.asyncio
async def test_complete_call_lifecycle(
    mock_redis: aioredis.Redis,
) -> None:
    """Complete call: connect → balance check → goodbye."""
    producer = AsyncMock()
    mgr = SessionManager(redis=mock_redis, producer=producer)

    # 1. Start session
    session = await mgr.on_session_start(
        "call-001", "+2348012345678",
    )
    assert session.customer_name == "Amina Bello"
    assert mgr.active_count == 1

    # 2. Balance check turn
    mock_result = ActionResult(
        success=True, message="Your balance is 15,000.50 NGN.",
    )
    mock_classification = AsyncMock()
    mock_classification.intent = "balance"
    mock_classification.confidence = 0.95

    with patch(
        "src.agents.supervisor.route_to_agent",
        return_value=(mock_result, mock_classification),
    ):
        from src.agents.supervisor import route_to_agent

        result, classification = await route_to_agent(
            "call-001", "Ina so in duba balance dina",
        )

    updated = await mgr.on_turn_complete(
        "call-001",
        "Ina so in duba balance dina",
        result.message,
        intent=classification.intent,
        confidence=classification.confidence,
        v2v_latency_ms=450.0,
        agent_name="balance_agent",
    )

    assert updated is not None
    assert len(updated.conversation_turns) == 2
    assert updated.current_intent == "balance"
    assert updated.confidence_history == [0.95]

    # 3. End session (goodbye)
    producer.publish.reset_mock()
    await mgr.on_session_end("call-001", "resolved")

    assert mgr.active_count == 0
    data = await mock_redis.get("session:call-001")
    assert data is None

    # Verify events: start event + end event
    producer.publish.assert_awaited_once()
    end_event = producer.publish.call_args[0][0]
    assert end_event.reason == "resolved"


@pytest.mark.asyncio
async def test_session_restart_after_shutdown(
    mock_redis: aioredis.Redis,
) -> None:
    """Session restart: start → turn → shutdown → restore → continue."""
    producer = AsyncMock()
    mgr1 = SessionManager(redis=mock_redis, producer=producer)

    # 1. Start and do one turn
    session = await mgr1.on_session_start(
        "call-002", "+2348087654321",
    )
    assert session.customer_name == "Musa Ibrahim"

    await mgr1.on_turn_complete(
        "call-002",
        "Check balance",
        "Your balance is 82,300 NGN.",
        intent="balance",
        confidence=0.92,
    )

    # 2. Graceful shutdown — persists remaining sessions
    for sid in mgr1.active_sessions:
        await mgr1.persist_for_shutdown(sid)

    # Verify session persisted with 1-hour TTL
    ttl = await mock_redis.ttl("session:call-002")
    assert ttl == 3600

    # 3. New instance restores session
    mgr2 = SessionManager(redis=mock_redis, producer=producer)
    restored = await mgr2.on_session_start(
        "call-002", "+2348087654321",
    )

    assert restored.session_id == "call-002"
    assert len(restored.conversation_turns) == 2
    assert restored.conversation_turns[0].content == "Check balance"
    assert restored.current_intent == "balance"

    # 4. Continue with another turn
    updated = await mgr2.on_turn_complete(
        "call-002",
        "Transfer 5000 to Amina",
        "Transfer of 5,000 NGN requires confirmation.",
        intent="transfer",
        confidence=0.88,
    )

    assert updated is not None
    assert len(updated.conversation_turns) == 4
    assert updated.current_intent == "transfer"
    assert updated.confidence_history == [0.92, 0.88]


@pytest.mark.asyncio
async def test_multiple_concurrent_sessions(
    mock_redis: aioredis.Redis,
) -> None:
    """Multiple sessions can run concurrently."""
    mgr = SessionManager(redis=mock_redis)

    await mgr.on_session_start("call-a", "+2348012345678")
    await mgr.on_session_start("call-b", "+2348087654321")

    assert mgr.active_count == 2
    assert "call-a" in mgr.active_sessions
    assert "call-b" in mgr.active_sessions

    await mgr.on_session_end("call-a", "resolved")
    assert mgr.active_count == 1

    await mgr.on_session_end("call-b", "hangup")
    assert mgr.active_count == 0


@pytest.mark.asyncio
async def test_session_with_escalation(
    mock_redis: aioredis.Redis,
) -> None:
    """Session escalation followed by end."""
    producer = AsyncMock()
    mgr = SessionManager(redis=mock_redis, producer=producer)

    await mgr.on_session_start(
        "call-esc", "+2348012345678",
    )
    await mgr.on_turn_complete(
        "call-esc",
        "I need help with a failed transfer",
        "Let me connect you to an agent.",
        intent="escalation",
        confidence=0.75,
        agent_name="general_agent",
    )
    await mgr.on_session_end("call-esc", "escalated")

    # Verify session cleaned up
    assert mgr.active_count == 0
    data = await mock_redis.get("session:call-esc")
    assert data is None
