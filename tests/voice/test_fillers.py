"""Tests for filler audio processor."""

from __future__ import annotations

import asyncio

import pytest
from pipecat.frames.frames import TextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection
from src.voice.fillers import FILLER_THRESHOLD_MS, FillerProcessor


@pytest.mark.asyncio
async def test_filler_triggers_above_threshold(filler: FillerProcessor) -> None:
    """Filler should trigger when response latency exceeds threshold."""
    filler.push_frame = lambda f, d=FrameDirection.DOWNSTREAM: asyncio.sleep(0)  # type: ignore[assignment]

    # Simulate speech start
    await filler.process_frame(
        TranscriptionFrame(text="hello", user_id="u1", timestamp="0"),
        FrameDirection.DOWNSTREAM,
    )

    # Simulate delay > 500ms
    await asyncio.sleep(0.6)

    # Simulate response
    await filler.process_frame(
        TextFrame(text="response"),
        FrameDirection.DOWNSTREAM,
    )

    assert filler.filler_was_triggered is True


@pytest.mark.asyncio
async def test_filler_does_not_trigger_below_threshold(
    filler: FillerProcessor,
) -> None:
    """Filler should not trigger when response is fast."""
    filler.push_frame = lambda f, d=FrameDirection.DOWNSTREAM: asyncio.sleep(0)  # type: ignore[assignment]

    await filler.process_frame(
        TranscriptionFrame(text="hello", user_id="u1", timestamp="0"),
        FrameDirection.DOWNSTREAM,
    )

    # No delay — immediate response
    await filler.process_frame(
        TextFrame(text="response"),
        FrameDirection.DOWNSTREAM,
    )

    assert filler.filler_was_triggered is False


def test_filler_threshold_value() -> None:
    """Threshold should be 500ms as specified."""
    assert FILLER_THRESHOLD_MS == 500.0
