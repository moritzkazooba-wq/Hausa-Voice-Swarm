"""Voice session lifecycle manager.

Manages session creation, turn tracking, and teardown. Stores SessionState
in Redis for cross-channel resumption (Project C), publishes Kafka events,
and instruments Prometheus metrics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import redis.asyncio as aioredis
import structlog

from src.api.mock_resolvers import get_customer
from src.config.settings import RedisSettings
from src.events.producer import KafkaEventProducer
from src.events.session_events import emit_session_ended, emit_session_started
from src.metrics.definitions import (
    active_voice_sessions,
    session_duration_seconds,
    voice_to_voice_latency_ms,
)
from src.models.session import AgentMessage, SessionState

logger = structlog.get_logger()

_SESSION_KEY_PREFIX = "session:"
_SHUTDOWN_TTL_SECONDS = 3600  # 1 hour for persisted sessions during shutdown


class SessionManager:
    """Manages voice session lifecycle with Redis persistence.

    Coordinates session start, turn updates, and teardown.
    Publishes Kafka events and instruments Prometheus metrics.
    """

    def __init__(
        self,
        *,
        redis: aioredis.Redis,
        producer: KafkaEventProducer | None = None,
        settings: RedisSettings | None = None,
    ) -> None:
        self._redis = redis
        self._producer = producer
        self._settings = settings or RedisSettings()
        self._active_sessions: set[str] = set()

    @property
    def active_sessions(self) -> set[str]:
        """Currently active session IDs."""
        return set(self._active_sessions)

    @property
    def active_count(self) -> int:
        """Number of currently active sessions."""
        return len(self._active_sessions)

    async def on_session_start(
        self,
        session_id: str,
        phone_number: str,
        *,
        channel: Literal["voice", "whatsapp", "ussd", "sms"] = "voice",
        language: Literal["ha", "en", "pcm"] = "ha",
    ) -> SessionState:
        """Start a new session or restore an existing one.

        Looks up customer via mock resolvers (replaced by real DB in Phase 3),
        creates SessionState in Redis, publishes SessionStartedEvent,
        and increments the active_voice_sessions gauge.

        Returns:
            The created or restored SessionState.
        """
        # Check for existing session (cross-channel resumption)
        existing = await self._get_session(session_id)
        if existing is not None:
            self._active_sessions.add(session_id)
            active_voice_sessions.inc()
            await logger.ainfo(
                "session_restored",
                session_id=session_id,
                turns=len(existing.conversation_turns),
            )
            return existing

        # Look up customer directly (internal operation, not via GraphQL)
        customer = await get_customer(phone_number)
        customer_name = customer.name if customer else "Unknown"

        session = SessionState(
            session_id=session_id,
            customer_phone=phone_number,
            customer_name=customer_name,
            language=language,
            current_intent="none",
            current_agent="none",
            conversation_turns=[],
            started_at=datetime.now(UTC),
            channel=channel,
            confidence_history=[],
        )

        await self._save_session(session)
        self._active_sessions.add(session_id)
        active_voice_sessions.inc()

        if self._producer is not None:
            await emit_session_started(
                self._producer,
                session_id=session_id,
                customer_phone=phone_number,
                channel=channel,
                language=language,
            )

        await logger.ainfo(
            "session_started",
            session_id=session_id,
            customer=customer_name,
            phone=phone_number,
        )

        return session

    async def on_turn_complete(
        self,
        session_id: str,
        user_text: str,
        agent_response: str,
        *,
        intent: str = "unknown",
        confidence: float = 0.0,
        v2v_latency_ms: float = 0.0,
        agent_name: str = "unknown",
    ) -> SessionState | None:
        """Record a completed conversation turn.

        Appends user and assistant messages to the session, updates intent
        and confidence, extends Redis TTL, and records v2v latency.

        Returns:
            Updated SessionState, or None if session not found.
        """
        session = await self._get_session(session_id)
        if session is None:
            await logger.awarning(
                "turn_complete_no_session", session_id=session_id,
            )
            return None

        now = datetime.now(UTC)

        # Append user turn
        session.conversation_turns.append(
            AgentMessage(
                role="user",
                content=user_text,
                timestamp=now,
                agent_name="caller",
            ),
        )

        # Append assistant turn
        session.conversation_turns.append(
            AgentMessage(
                role="assistant",
                content=agent_response,
                timestamp=now,
                agent_name=agent_name,
            ),
        )

        session.current_intent = intent
        session.current_agent = agent_name
        session.confidence_history.append(confidence)

        # Save and extend TTL
        await self._save_session(session)

        # Record v2v latency metric
        if v2v_latency_ms > 0:
            voice_to_voice_latency_ms.observe(v2v_latency_ms)

        await logger.ainfo(
            "turn_complete",
            session_id=session_id,
            intent=intent,
            turns=len(session.conversation_turns),
            v2v_ms=round(v2v_latency_ms, 1),
        )

        return session

    async def on_session_end(
        self,
        session_id: str,
        reason: Literal["hangup", "timeout", "resolved", "escalated"],
    ) -> None:
        """End a session: record duration, publish event, cleanup.

        Calculates session duration, publishes SessionEndedEvent,
        decrements the gauge, and removes session from Redis.
        """
        session = await self._get_session(session_id)
        self._active_sessions.discard(session_id)

        if session is not None:
            duration = (
                datetime.now(UTC) - session.started_at
            ).total_seconds()
            total_turns = len(session.conversation_turns)

            session_duration_seconds.observe(duration)

            if self._producer is not None:
                await emit_session_ended(
                    self._producer,
                    session_id=session_id,
                    reason=reason,
                    duration_seconds=duration,
                    total_turns=total_turns,
                )

            await logger.ainfo(
                "session_ended",
                session_id=session_id,
                reason=reason,
                duration_s=round(duration, 1),
                turns=total_turns,
            )

        # Cleanup Redis
        key = f"{_SESSION_KEY_PREFIX}{session_id}"
        await self._redis.delete(key)
        active_voice_sessions.dec()

    async def persist_for_shutdown(self, session_id: str) -> bool:
        """Persist a session with extended TTL for graceful shutdown.

        Sets 1-hour TTL so the session can be resumed after restart.

        Returns:
            True if session was persisted, False if not found.
        """
        key = f"{_SESSION_KEY_PREFIX}{session_id}"
        exists = await self._redis.exists(key)
        if exists:
            await self._redis.expire(key, _SHUTDOWN_TTL_SECONDS)
            await logger.ainfo(
                "session_persisted_for_shutdown",
                session_id=session_id,
                ttl_seconds=_SHUTDOWN_TTL_SECONDS,
            )
            return True
        return False

    # ── Redis helpers ────────────────────────────────────────────────

    async def _get_session(self, session_id: str) -> SessionState | None:
        """Load session from Redis."""
        key = f"{_SESSION_KEY_PREFIX}{session_id}"
        data = await self._redis.get(key)
        if data is None:
            return None
        raw = data if isinstance(data, str) else data.decode("utf-8")
        return SessionState.model_validate_json(raw)

    async def _save_session(
        self,
        session: SessionState,
        *,
        ttl: int | None = None,
    ) -> None:
        """Save session to Redis with TTL."""
        key = f"{_SESSION_KEY_PREFIX}{session.session_id}"
        ttl = ttl or self._settings.session_ttl_seconds
        await self._redis.set(
            key,
            session.model_dump_json(),
            ex=ttl,
        )
