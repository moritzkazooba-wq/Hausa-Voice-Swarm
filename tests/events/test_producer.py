"""Tests for Kafka event producer with mock."""

from unittest.mock import AsyncMock, patch

import pytest
from src.events.producer import (
    TOPIC_ESCALATIONS,
    TOPIC_INTENTS,
    TOPIC_SESSIONS,
    TOPIC_TOOLS,
    KafkaEventProducer,
)
from src.events.schemas import (
    EscalationTriggeredEvent,
    IntentClassifiedEvent,
    SessionEndedEvent,
    SessionStartedEvent,
    ToolExecutedEvent,
)


@pytest.fixture
def mock_producer() -> KafkaEventProducer:
    """Create a KafkaEventProducer with mocked internals."""
    producer = KafkaEventProducer()
    producer._producer = AsyncMock()
    producer._producer.send_and_wait = AsyncMock()
    return producer


class TestKafkaEventProducer:
    async def test_publish_intent_classified(self, mock_producer: KafkaEventProducer) -> None:
        event = IntentClassifiedEvent(
            session_id="sess-1",
            utterance="Ina so in duba balance na",
            intent="balance_check",
            confidence=0.92,
            language="ha",
            model_used="test-model",
        )
        await mock_producer.publish(event)

        mock_producer._producer.send_and_wait.assert_called_once()  # type: ignore[union-attr]
        call_kwargs = mock_producer._producer.send_and_wait.call_args  # type: ignore[union-attr]
        assert call_kwargs.kwargs["topic"] == TOPIC_INTENTS
        assert call_kwargs.kwargs["key"] == "sess-1"

    async def test_publish_tool_executed(self, mock_producer: KafkaEventProducer) -> None:
        event = ToolExecutedEvent(
            session_id="sess-2",
            agent_name="balance_agent",
            tool_name="check_balance",
            success=True,
            duration_ms=45.0,
            result_summary="5000 NGN",
        )
        await mock_producer.publish(event)

        call_kwargs = mock_producer._producer.send_and_wait.call_args  # type: ignore[union-attr]
        assert call_kwargs.kwargs["topic"] == TOPIC_TOOLS

    async def test_publish_session_started(self, mock_producer: KafkaEventProducer) -> None:
        event = SessionStartedEvent(
            session_id="sess-3",
            customer_phone="+2348012345678",
            channel="voice",
            language="ha",
        )
        await mock_producer.publish(event)

        call_kwargs = mock_producer._producer.send_and_wait.call_args  # type: ignore[union-attr]
        assert call_kwargs.kwargs["topic"] == TOPIC_SESSIONS

    async def test_publish_session_ended(self, mock_producer: KafkaEventProducer) -> None:
        event = SessionEndedEvent(
            session_id="sess-4",
            reason="resolved",
            duration_seconds=120.0,
            total_turns=10,
        )
        await mock_producer.publish(event)

        call_kwargs = mock_producer._producer.send_and_wait.call_args  # type: ignore[union-attr]
        assert call_kwargs.kwargs["topic"] == TOPIC_SESSIONS

    async def test_publish_escalation(self, mock_producer: KafkaEventProducer) -> None:
        event = EscalationTriggeredEvent(
            session_id="sess-5",
            from_agent="transfer_agent",
            reason="Fraud suspected",
            customer_phone="+2348012345678",
            priority="critical",
        )
        await mock_producer.publish(event)

        call_kwargs = mock_producer._producer.send_and_wait.call_args  # type: ignore[union-attr]
        assert call_kwargs.kwargs["topic"] == TOPIC_ESCALATIONS

    async def test_publish_serializes_json(self, mock_producer: KafkaEventProducer) -> None:
        event = IntentClassifiedEvent(
            session_id="sess-6",
            utterance="hello",
            intent="greeting",
            confidence=0.99,
            language="en",
            model_used="test",
        )
        await mock_producer.publish(event)

        call_kwargs = mock_producer._producer.send_and_wait.call_args  # type: ignore[union-attr]
        payload = call_kwargs.kwargs["value"]
        assert isinstance(payload, str)
        assert '"event_type":"intent_classified"' in payload.replace(" ", "")

    async def test_publish_without_start_logs_warning(self) -> None:
        producer = KafkaEventProducer()
        event = IntentClassifiedEvent(
            session_id="sess-7",
            utterance="test",
            intent="test",
            confidence=0.5,
            language="en",
            model_used="test",
        )
        # Should not raise — just logs warning
        await producer.publish(event)

    async def test_start_and_stop(self) -> None:
        producer = KafkaEventProducer()
        with patch("src.events.producer.AIOKafkaProducer") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value = mock_instance
            await producer.start()
            mock_instance.start.assert_called_once()

            await producer.stop()
            mock_instance.stop.assert_called_once()
            assert producer._producer is None
