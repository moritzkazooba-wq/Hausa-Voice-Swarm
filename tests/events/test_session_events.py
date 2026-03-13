"""Tests for session event helper functions."""

from __future__ import annotations

from src.events.producer import KafkaEventProducer
from src.events.session_events import (
    emit_escalation,
    emit_intent_classified,
    emit_session_ended,
    emit_session_started,
    emit_tool_executed,
)


class TestSessionEventHelpers:
    async def test_emit_intent_classified(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_intent_classified(
            mock_kafka_producer,
            session_id="sess-1",
            utterance="Ina so in duba",
            intent="balance_check",
            confidence=0.9,
            language="ha",
            model_used="test-model",
        )
        mock_kafka_producer.publish.assert_called_once()  # type: ignore[union-attr]
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.event_type == "intent_classified"
        assert event.session_id == "sess-1"
        assert event.intent == "balance_check"

    async def test_emit_tool_executed(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_tool_executed(
            mock_kafka_producer,
            session_id="sess-2",
            agent_name="balance_agent",
            tool_name="check_balance",
            success=True,
            duration_ms=50.0,
            result_summary="OK",
        )
        mock_kafka_producer.publish.assert_called_once()  # type: ignore[union-attr]
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.event_type == "tool_executed"
        assert event.agent_name == "balance_agent"

    async def test_emit_tool_executed_with_metadata(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_tool_executed(
            mock_kafka_producer,
            session_id="sess-2",
            agent_name="transfer_agent",
            tool_name="send_money",
            success=False,
            duration_ms=100.0,
            result_summary="Failed",
            metadata={"error": "insufficient_funds"},
        )
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.metadata == {"error": "insufficient_funds"}

    async def test_emit_session_started(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_session_started(
            mock_kafka_producer,
            session_id="sess-3",
            customer_phone="+2348012345678",
            channel="voice",
            language="ha",
        )
        mock_kafka_producer.publish.assert_called_once()  # type: ignore[union-attr]
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.event_type == "session_started"
        assert event.channel == "voice"

    async def test_emit_session_ended(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_session_ended(
            mock_kafka_producer,
            session_id="sess-4",
            reason="resolved",
            duration_seconds=180.0,
            total_turns=12,
        )
        mock_kafka_producer.publish.assert_called_once()  # type: ignore[union-attr]
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.event_type == "session_ended"
        assert event.total_turns == 12

    async def test_emit_escalation(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_escalation(
            mock_kafka_producer,
            session_id="sess-5",
            from_agent="transfer_agent",
            reason="Dispute",
            customer_phone="+2348012345678",
            priority="high",
        )
        mock_kafka_producer.publish.assert_called_once()  # type: ignore[union-attr]
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.event_type == "escalation_triggered"
        assert event.priority == "high"

    async def test_emit_escalation_default_priority(
        self, mock_kafka_producer: KafkaEventProducer
    ) -> None:
        await emit_escalation(
            mock_kafka_producer,
            session_id="sess-6",
            from_agent="general_agent",
            reason="Unknown issue",
            customer_phone="+2348099999999",
        )
        event = mock_kafka_producer.publish.call_args[0][0]  # type: ignore[union-attr]
        assert event.priority == "medium"
