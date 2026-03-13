"""Async Kafka event consumers using aiokafka."""

from abc import ABC, abstractmethod

import structlog
from aiokafka import AIOKafkaConsumer

from src.config.settings import KafkaSettings

logger = structlog.get_logger()


class BaseKafkaConsumer(ABC):
    """Base async Kafka consumer with graceful startup/shutdown."""

    def __init__(
        self,
        *topics: str,
        group_id: str,
        settings: KafkaSettings | None = None,
    ) -> None:
        self._settings = settings or KafkaSettings()
        self._topics = topics
        self._group_id = group_id
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the underlying aiokafka consumer."""
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda v: v.decode("utf-8"),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        await logger.ainfo("kafka_consumer_started", topics=self._topics, group_id=self._group_id)

    async def stop(self) -> None:
        """Gracefully stop the consumer."""
        self._running = False
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            await logger.ainfo("kafka_consumer_stopped", group_id=self._group_id)

    async def run(self) -> None:
        """Consume messages in a loop until stopped."""
        if self._consumer is None:
            await logger.aerror("consumer_not_started")
            return

        async for msg in self._consumer:
            if not self._running:
                break
            await self.handle_message(msg.topic, msg.value, msg.key)

    @abstractmethod
    async def handle_message(self, topic: str, value: str, key: bytes | None) -> None:
        """Process a single consumed message. Subclasses must implement."""
        ...


class AnalyticsConsumer(BaseKafkaConsumer):
    """Placeholder consumer for Project C ops dashboard analytics pipeline."""

    def __init__(self, settings: KafkaSettings | None = None) -> None:
        super().__init__(
            "hsv.intents",
            "hsv.tools",
            "hsv.sessions",
            "hsv.escalations",
            group_id="hsv-analytics",
            settings=settings,
        )

    async def handle_message(self, topic: str, value: str, key: bytes | None) -> None:
        """Forward events to analytics pipeline (placeholder)."""
        await logger.ainfo(
            "analytics_event_received",
            topic=topic,
            key=key,
        )
