"""Tests for AgentBridgeProcessor."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection
from src.models.transaction import ActionResult
from src.voice.agent_bridge import AgentBridgeProcessor


@pytest.mark.asyncio
async def test_bridge_processes_transcription_to_text(
    bridge: AgentBridgeProcessor,
) -> None:
    """TranscriptionFrame should produce a TextFrame via route_to_agent."""
    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    bridge.push_frame = capture  # type: ignore[assignment]

    mock_result = ActionResult(success=True, message="Your balance is 5000 NGN.")
    mock_classification = AsyncMock()
    mock_classification.intent = "balance"
    mock_classification.confidence = 0.95

    with patch(
        "src.voice.agent_bridge.route_to_agent",
        return_value=(mock_result, mock_classification),
    ):
        await bridge.process_frame(
            TranscriptionFrame(text="Check balance", user_id="u1", timestamp="0"),
            FrameDirection.DOWNSTREAM,
        )

    assert len(pushed) == 1
    assert isinstance(pushed[0], TextFrame)
    assert pushed[0].text == "Your balance is 5000 NGN."
    assert bridge.last_classification is not None
    assert bridge.last_classification.intent == "balance"


@pytest.mark.asyncio
async def test_bridge_passes_through_other_frames(
    bridge: AgentBridgeProcessor,
) -> None:
    """Non-TranscriptionFrame should pass through unchanged."""
    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    bridge.push_frame = capture  # type: ignore[assignment]

    text_frame = TextFrame(text="passthrough")
    await bridge.process_frame(text_frame, FrameDirection.DOWNSTREAM)

    assert len(pushed) == 1
    assert pushed[0] is text_frame


@pytest.mark.asyncio
async def test_bridge_calls_route_to_agent_with_session_id(
    bridge: AgentBridgeProcessor,
) -> None:
    """route_to_agent should be called with the correct session_id."""
    bridge.push_frame = AsyncMock()  # type: ignore[assignment]

    mock_result = ActionResult(success=True, message="Done.")
    mock_classification = AsyncMock()
    mock_classification.intent = "general"
    mock_classification.confidence = 0.85

    with patch(
        "src.voice.agent_bridge.route_to_agent",
        return_value=(mock_result, mock_classification),
    ) as mock_route:
        await bridge.process_frame(
            TranscriptionFrame(text="hello", user_id="u1", timestamp="0"),
            FrameDirection.DOWNSTREAM,
        )

    mock_route.assert_awaited_once_with("test-session-001", "hello")


@pytest.mark.asyncio
async def test_bridge_handles_route_to_agent_error(
    bridge: AgentBridgeProcessor,
) -> None:
    """When route_to_agent raises, bridge should push a fallback TextFrame."""
    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    bridge.push_frame = capture  # type: ignore[assignment]

    with patch(
        "src.voice.agent_bridge.route_to_agent",
        side_effect=RuntimeError("supervisor crashed"),
    ):
        await bridge.process_frame(
            TranscriptionFrame(text="hello", user_id="u1", timestamp="0"),
            FrameDirection.DOWNSTREAM,
        )

    assert len(pushed) == 1
    assert isinstance(pushed[0], TextFrame)
    assert "sorry" in pushed[0].text.lower()
