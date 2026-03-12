"""Kafka event producers, consumers, and schemas."""

from src.events.consumer import AnalyticsConsumer, BaseKafkaConsumer
from src.events.producer import (
    TOPIC_ESCALATIONS,
    TOPIC_INTENTS,
    TOPIC_SESSIONS,
    TOPIC_TOOLS,
    KafkaEventProducer,
)
from src.events.schemas import (
    BaseEvent,
    EscalationTriggeredEvent,
    IntentClassifiedEvent,
    SessionEndedEvent,
    SessionStartedEvent,
    ToolExecutedEvent,
)
from src.events.session_events import (
    emit_escalation,
    emit_intent_classified,
    emit_session_ended,
    emit_session_started,
    emit_tool_executed,
)

__all__ = [
    "TOPIC_ESCALATIONS",
    "TOPIC_INTENTS",
    "TOPIC_SESSIONS",
    "TOPIC_TOOLS",
    "AnalyticsConsumer",
    "BaseEvent",
    "BaseKafkaConsumer",
    "EscalationTriggeredEvent",
    "IntentClassifiedEvent",
    "KafkaEventProducer",
    "SessionEndedEvent",
    "SessionStartedEvent",
    "ToolExecutedEvent",
    "emit_escalation",
    "emit_intent_classified",
    "emit_session_ended",
    "emit_session_started",
    "emit_tool_executed",
]
