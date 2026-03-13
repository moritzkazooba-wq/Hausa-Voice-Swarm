"""Helper functions for emitting session lifecycle and agent events."""

from typing import Literal

import structlog

from src.events.producer import KafkaEventProducer
from src.events.schemas import (
    EscalationTriggeredEvent,
    IntentClassifiedEvent,
    SessionEndedEvent,
    SessionStartedEvent,
    ToolExecutedEvent,
)
from src.models.session import MetadataDict

logger = structlog.get_logger()


async def emit_intent_classified(
    producer: KafkaEventProducer,
    *,
    session_id: str,
    utterance: str,
    intent: str,
    confidence: float,
    language: Literal["ha", "en", "pcm"],
    model_used: str,
) -> None:
    """Emit an IntentClassifiedEvent after classification."""
    event = IntentClassifiedEvent(
        session_id=session_id,
        utterance=utterance,
        intent=intent,
        confidence=confidence,
        language=language,
        model_used=model_used,
    )
    await producer.publish(event)


async def emit_tool_executed(
    producer: KafkaEventProducer,
    *,
    session_id: str,
    agent_name: str,
    tool_name: str,
    success: bool,
    duration_ms: float,
    result_summary: str,
    metadata: MetadataDict | None = None,
) -> None:
    """Emit a ToolExecutedEvent after a domain agent action."""
    event = ToolExecutedEvent(
        session_id=session_id,
        agent_name=agent_name,
        tool_name=tool_name,
        success=success,
        duration_ms=duration_ms,
        result_summary=result_summary,
        metadata=metadata or {},
    )
    await producer.publish(event)


async def emit_session_started(
    producer: KafkaEventProducer,
    *,
    session_id: str,
    customer_phone: str,
    channel: Literal["voice", "whatsapp", "ussd", "sms"],
    language: Literal["ha", "en", "pcm"],
) -> None:
    """Emit a SessionStartedEvent when a new session begins."""
    event = SessionStartedEvent(
        session_id=session_id,
        customer_phone=customer_phone,
        channel=channel,
        language=language,
    )
    await producer.publish(event)


async def emit_session_ended(
    producer: KafkaEventProducer,
    *,
    session_id: str,
    reason: Literal["hangup", "timeout", "resolved", "escalated"],
    duration_seconds: float,
    total_turns: int,
) -> None:
    """Emit a SessionEndedEvent when a session closes."""
    event = SessionEndedEvent(
        session_id=session_id,
        reason=reason,
        duration_seconds=duration_seconds,
        total_turns=total_turns,
    )
    await producer.publish(event)


async def emit_escalation(
    producer: KafkaEventProducer,
    *,
    session_id: str,
    from_agent: str,
    reason: str,
    customer_phone: str,
    priority: Literal["low", "medium", "high", "critical"] = "medium",
) -> None:
    """Emit an EscalationTriggeredEvent."""
    event = EscalationTriggeredEvent(
        session_id=session_id,
        from_agent=from_agent,
        reason=reason,
        customer_phone=customer_phone,
        priority=priority,
    )
    await producer.publish(event)
