"""Kafka event schemas consumed by Project C ops dashboard."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.models.session import MetadataDict


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BaseEvent(BaseModel):
    """Base for all Kafka events."""

    model_config = ConfigDict(strict=True)

    session_id: str
    timestamp: datetime = Field(default_factory=_utcnow)


class IntentClassifiedEvent(BaseEvent):
    """Emitted after intent classification completes."""

    event_type: Literal["intent_classified"] = "intent_classified"
    utterance: str
    intent: str
    confidence: float
    language: Literal["ha", "en", "pcm"]
    model_used: str


class ToolExecutedEvent(BaseEvent):
    """Emitted after a domain agent executes a tool/action."""

    event_type: Literal["tool_executed"] = "tool_executed"
    agent_name: str
    tool_name: str
    success: bool
    duration_ms: float
    result_summary: str
    metadata: MetadataDict = Field(default_factory=dict)


class SessionStartedEvent(BaseEvent):
    """Emitted when a new voice/chat session begins."""

    event_type: Literal["session_started"] = "session_started"
    customer_phone: str
    channel: Literal["voice", "whatsapp", "ussd", "sms"]
    language: Literal["ha", "en", "pcm"]


class SessionEndedEvent(BaseEvent):
    """Emitted when a session ends (hang-up, timeout, or agent close)."""

    event_type: Literal["session_ended"] = "session_ended"
    reason: Literal["hangup", "timeout", "resolved", "escalated"]
    duration_seconds: float
    total_turns: int


class EscalationTriggeredEvent(BaseEvent):
    """Emitted when a session is escalated to a human agent."""

    event_type: Literal["escalation_triggered"] = "escalation_triggered"
    from_agent: str
    reason: str
    customer_phone: str
    priority: Literal["low", "medium", "high", "critical"] = "medium"
