"""Tests for SessionState and AgentMessage models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from src.models.session import AgentMessage, SessionState


class TestAgentMessage:
    """AgentMessage validation tests."""

    def test_valid_message(self) -> None:
        msg = AgentMessage(
            role="user",
            content="Ina so in biya kuɗi",
            timestamp=datetime.now(tz=UTC),
            agent_name="orchestrator",
        )
        assert msg.role == "user"
        assert msg.metadata == {}

    def test_with_metadata(self) -> None:
        msg = AgentMessage(
            role="assistant",
            content="Your balance is 15,000 NGN",
            timestamp=datetime.now(tz=UTC),
            agent_name="balance_agent",
            metadata={"confidence": 0.95, "intent": "balance_check"},
        )
        assert msg.metadata["confidence"] == 0.95

    def test_invalid_role(self) -> None:
        with pytest.raises(ValidationError):
            AgentMessage(
                role="tool",  # type: ignore[arg-type]
                content="test",
                timestamp=datetime.now(tz=UTC),
                agent_name="test",
            )

    def test_serialization_roundtrip(self) -> None:
        msg = AgentMessage(
            role="system",
            content="Session started",
            timestamp=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
            agent_name="system",
            metadata={"event": "start"},
        )
        json_str = msg.model_dump_json()
        restored = AgentMessage.model_validate_json(json_str)
        assert restored == msg


class TestSessionState:
    """SessionState validation tests."""

    def _valid_data(self) -> dict:  # type: ignore[type-arg]
        return {
            "session_id": "sess-001",
            "customer_phone": "+2348012345678",
            "customer_name": "Amina",
            "language": "ha",
            "current_intent": "balance_check",
            "current_agent": "balance_agent",
            "started_at": datetime.now(tz=UTC),
            "channel": "voice",
        }

    def test_valid_session(self) -> None:
        session = SessionState(**self._valid_data())
        assert session.language == "ha"
        assert session.conversation_turns == []
        assert session.confidence_history == []

    def test_with_turns(self) -> None:
        data = self._valid_data()
        data["conversation_turns"] = [
            AgentMessage(
                role="user",
                content="Check my balance",
                timestamp=datetime.now(tz=UTC),
                agent_name="orchestrator",
            )
        ]
        session = SessionState(**data)
        assert len(session.conversation_turns) == 1

    def test_invalid_language(self) -> None:
        data = self._valid_data()
        data["language"] = "fr"
        with pytest.raises(ValidationError):
            SessionState(**data)

    def test_invalid_channel(self) -> None:
        data = self._valid_data()
        data["channel"] = "email"
        with pytest.raises(ValidationError):
            SessionState(**data)

    def test_all_channels_valid(self) -> None:
        for channel in ("voice", "whatsapp", "ussd", "sms"):
            data = self._valid_data()
            data["channel"] = channel
            session = SessionState(**data)
            assert session.channel == channel

    def test_confidence_history(self) -> None:
        data = self._valid_data()
        data["confidence_history"] = [0.85, 0.92, 0.78]
        session = SessionState(**data)
        assert session.confidence_history == [0.85, 0.92, 0.78]

    def test_serialization_roundtrip(self) -> None:
        data = self._valid_data()
        data["conversation_turns"] = [
            AgentMessage(
                role="user",
                content="Hello",
                timestamp=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
                agent_name="orchestrator",
            )
        ]
        data["confidence_history"] = [0.9]
        session = SessionState(**data)
        json_str = session.model_dump_json()
        restored = SessionState.model_validate_json(json_str)
        assert restored == session
