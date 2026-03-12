"""Async Kafka event producer using aiokafka."""

import structlog
from aiokafka import AIOKafkaProducer

from src.config.settings import KafkaSettings
from src.events.schemas import BaseEvent

logger = structlog.get_logger()

# Topic constants
TOPIC_INTENTS = "hsv.intents"
TOPIC_TOOLS = "hsv.tools"
TOPIC_SESSIONS = "hsv.sessions"
TOPIC_ESCALATIONS = "hsv.escalations"

# Map event_type → topic
_EVENT_TOPIC_MAP: dict[str, str] = {
    "intent_classified": TOPIC_INTENTS,
    "tool_executed": TOPIC_TOOLS,
    "session_started": TOPIC_SESSIONS,
    "session_ended": TOPIC_SESSIONS,
    "escalation_triggered": TOPIC_ESCALATIONS,
}


class KafkaEventProducer:
    """Async Kafka producer with graceful startup/shutdown."""

    def __init__(self, settings: KafkaSettings | None = None) -> None:
        self._settings = settings or KafkaSettings()
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the underlying aiokafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            value_serializer=lambda v: v.encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        await logger.ainfo("kafka_producer_started")

    async def stop(self) -> None:
        """Gracefully flush and stop the producer."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            await logger.ainfo("kafka_producer_stopped")

    async def publish(self, event: BaseEvent) -> None:
        """Publish a Pydantic event to the appropriate Kafka topic.

        The topic is determined by the event's ``event_type`` field.
        The event is serialized to JSON.
        """
        if self._producer is None:
            evt_type = getattr(event, "event_type", "unknown")
            await logger.awarn("kafka_producer_not_started", event_type=evt_type)
            return

        event_type: str = getattr(event, "event_type", "unknown")
        topic = _EVENT_TOPIC_MAP.get(event_type)
        if topic is None:
            await logger.aerror("unknown_event_type", event_type=event_type)
            return

        payload = event.model_dump_json()
        await self._producer.send_and_wait(
            topic=topic,
            value=payload,
            key=event.session_id,
        )
        await logger.ainfo(
            "event_published",
            topic=topic,
            event_type=event_type,
            session_id=event.session_id,
        )
