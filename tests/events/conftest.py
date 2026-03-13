"""Events test fixtures — mock Kafka producers for transport-level tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from src.events.producer import KafkaEventProducer


@pytest.fixture
def mock_producer() -> KafkaEventProducer:
    """KafkaEventProducer with mocked internal transport for topic-routing tests.

    Use this when testing the producer's serialisation and topic routing.
    For higher-level tests that only need to record published events, prefer
    ``mock_kafka_producer`` from the root conftest.
    """
    producer = KafkaEventProducer()
    producer._producer = AsyncMock()
    producer._producer.send_and_wait = AsyncMock()
    return producer
