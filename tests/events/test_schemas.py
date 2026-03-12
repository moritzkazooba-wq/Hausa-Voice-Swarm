"""Tests for Kafka event schemas."""

from datetime import datetime

from src.events.schemas import (
    BaseEvent,
    EscalationTriggeredEvent,
    IntentClassifiedEvent,
    SessionEndedEvent,
    SessionStartedEvent,
    ToolExecutedEvent,
)


class TestBaseEvent:
    def test_default_timestamp(self) -> None:
        event = BaseEvent(session_id="sess-1")
        assert isinstance(event.timestamp, datetime)

    def test_explicit_timestamp(self) -> None:
        ts = datetime(2024, 1, 1, 12, 0, 0)
        event = BaseEvent(session_id="sess-1", timestamp=ts)
        assert event.timestamp == ts


class TestIntentClassifiedEvent:
    def test_fields_and_event_type(self) -> None:
        event = IntentClassifiedEvent(
            session_id="sess-1",
            utterance="Ina so in biya kuɗi",
            intent="balance_check",
            confidence=0.92,
            language="ha",
            model_used="paraphrase-multilingual-MiniLM-L12-v2",
        )
        assert event.event_type == "intent_classified"
        assert event.intent == "balance_check"
        assert event.confidence == 0.92
        assert event.language == "ha"

    def test_json_roundtrip(self) -> None:
        event = IntentClassifiedEvent(
            session_id="sess-2",
            utterance="check balance",
            intent="balance_check",
            confidence=0.85,
            language="en",
            model_used="test-model",
        )
        raw = event.model_dump_json()
        assert '"intent_classified"' in raw
        restored = IntentClassifiedEvent.model_validate_json(raw)
        assert restored.utterance == event.utterance
        assert restored.session_id == "sess-2"


class TestToolExecutedEvent:
    def test_fields_and_defaults(self) -> None:
        event = ToolExecutedEvent(
            session_id="sess-1",
            agent_name="balance_agent",
            tool_name="check_balance",
            success=True,
            duration_ms=45.2,
            result_summary="Balance: 5000 NGN",
        )
        assert event.event_type == "tool_executed"
        assert event.metadata == {}

    def test_with_metadata(self) -> None:
        event = ToolExecutedEvent(
            session_id="sess-1",
            agent_name="transfer_agent",
            tool_name="send_money",
            success=False,
            duration_ms=120.0,
            result_summary="Insufficient funds",
            metadata={"error_code": "INSUFFICIENT_FUNDS"},
        )
        assert event.metadata["error_code"] == "INSUFFICIENT_FUNDS"

    def test_json_roundtrip(self) -> None:
        event = ToolExecutedEvent(
            session_id="sess-3",
            agent_name="bills_agent",
            tool_name="pay_bill",
            success=True,
            duration_ms=80.0,
            result_summary="Bill paid",
        )
        raw = event.model_dump_json()
        assert '"tool_executed"' in raw
        restored = ToolExecutedEvent.model_validate_json(raw)
        assert restored.agent_name == "bills_agent"


class TestSessionStartedEvent:
    def test_fields(self) -> None:
        event = SessionStartedEvent(
            session_id="sess-1",
            customer_phone="+2348012345678",
            channel="voice",
            language="ha",
        )
        assert event.event_type == "session_started"
        assert event.channel == "voice"

    def test_json_roundtrip(self) -> None:
        event = SessionStartedEvent(
            session_id="sess-4",
            customer_phone="+2348099999999",
            channel="whatsapp",
            language="pcm",
        )
        raw = event.model_dump_json()
        restored = SessionStartedEvent.model_validate_json(raw)
        assert restored.customer_phone == "+2348099999999"


class TestSessionEndedEvent:
    def test_fields(self) -> None:
        event = SessionEndedEvent(
            session_id="sess-1",
            reason="resolved",
            duration_seconds=120.5,
            total_turns=8,
        )
        assert event.event_type == "session_ended"
        assert event.total_turns == 8

    def test_json_roundtrip(self) -> None:
        event = SessionEndedEvent(
            session_id="sess-5",
            reason="hangup",
            duration_seconds=30.0,
            total_turns=3,
        )
        raw = event.model_dump_json()
        restored = SessionEndedEvent.model_validate_json(raw)
        assert restored.reason == "hangup"


class TestEscalationTriggeredEvent:
    def test_fields_and_default_priority(self) -> None:
        event = EscalationTriggeredEvent(
            session_id="sess-1",
            from_agent="transfer_agent",
            reason="Customer disputes transaction",
            customer_phone="+2348012345678",
        )
        assert event.event_type == "escalation_triggered"
        assert event.priority == "medium"

    def test_custom_priority(self) -> None:
        event = EscalationTriggeredEvent(
            session_id="sess-1",
            from_agent="transfer_agent",
            reason="Fraud detected",
            customer_phone="+2348012345678",
            priority="critical",
        )
        assert event.priority == "critical"

    def test_json_roundtrip(self) -> None:
        event = EscalationTriggeredEvent(
            session_id="sess-6",
            from_agent="general_agent",
            reason="Unrecognized request",
            customer_phone="+2348011111111",
            priority="low",
        )
        raw = event.model_dump_json()
        restored = EscalationTriggeredEvent.model_validate_json(raw)
        assert restored.from_agent == "general_agent"
