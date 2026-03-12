"""Session and conversation models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentMessage(BaseModel):
    """Single message in a conversation turn."""

    model_config = ConfigDict(strict=True)

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    agent_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    """Active voice/chat session state (stored in Redis)."""

    model_config = ConfigDict(strict=True)

    session_id: str
    customer_phone: str
    customer_name: str
    language: Literal["ha", "en", "pcm"]
    current_intent: str
    current_agent: str
    conversation_turns: list[AgentMessage] = Field(default_factory=list)
    started_at: datetime
    channel: Literal["voice", "whatsapp", "ussd", "sms"]
    confidence_history: list[float] = Field(default_factory=list)
