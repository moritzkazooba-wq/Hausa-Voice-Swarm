"""Voice test fixtures (Layer 4) — transport, pipeline, processors."""

from __future__ import annotations

import pytest
from src.voice.agent_bridge import AgentBridgeProcessor
from src.voice.fillers import FillerProcessor
from src.voice.transport import StubTransport


@pytest.fixture
def stub_transport() -> StubTransport:
    """StubTransport with default text queue for pipeline testing."""
    return StubTransport("test input")


@pytest.fixture
def bridge() -> AgentBridgeProcessor:
    """AgentBridgeProcessor bound to a test session."""
    return AgentBridgeProcessor(session_id="test-session-001")


@pytest.fixture
def filler() -> FillerProcessor:
    """FillerProcessor for latency threshold testing."""
    return FillerProcessor()
