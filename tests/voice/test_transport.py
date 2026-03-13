"""Tests for StubTransport and transport factory."""

from __future__ import annotations

import pytest
from pipecat.frames.frames import TextFrame
from pipecat.processors.frame_processor import FrameDirection
from src.voice.transport import (
    StubInputTransport,
    StubOutputTransport,
    StubTransport,
    create_transport,
)


@pytest.mark.asyncio
async def test_stub_transport_creates_processors() -> None:
    transport = StubTransport("hello")
    assert transport.input() is not None
    assert transport.output() is not None


@pytest.mark.asyncio
async def test_stub_input_passes_frames_through() -> None:
    """StubInputTransport passes all frames through unchanged."""
    input_proc = StubInputTransport()
    pushed: list[object] = []

    async def capture_push(
        frame: object,
        direction: FrameDirection = FrameDirection.DOWNSTREAM,
    ) -> None:
        pushed.append(frame)

    input_proc.push_frame = capture_push  # type: ignore[assignment]

    text_frame = TextFrame(text="test")
    await input_proc.process_frame(text_frame, FrameDirection.DOWNSTREAM)

    assert len(pushed) == 1
    assert pushed[0] is text_frame


@pytest.mark.asyncio
async def test_stub_output_captures_text_and_sets_event() -> None:
    """StubOutputTransport captures TextFrame and sets response_ready."""
    output_proc = StubOutputTransport()
    assert not output_proc.response_ready.is_set()

    # Mock push_frame to avoid pipeline errors
    async def noop(f: object, d: object = None) -> None:
        pass

    output_proc.push_frame = noop  # type: ignore[assignment]

    await output_proc.process_frame(
        TextFrame(text="response text"),
        FrameDirection.DOWNSTREAM,
    )

    assert output_proc.response_ready.is_set()
    assert output_proc.collected_text == "response text"


@pytest.mark.asyncio
async def test_stub_transport_response_ready_event() -> None:
    transport = StubTransport("input")
    assert not transport.response_ready.is_set()
    assert transport.collected_text == ""


@pytest.mark.asyncio
async def test_create_transport_stub_provider() -> None:
    from src.config.settings import TelephonySettings

    settings = TelephonySettings(telephony_provider="stub")
    transport = create_transport(settings, input_text="test")
    assert isinstance(transport, StubTransport)


@pytest.mark.asyncio
async def test_create_transport_daily_raises() -> None:
    from src.config.settings import TelephonySettings

    settings = TelephonySettings(telephony_provider="daily")
    with pytest.raises(NotImplementedError, match="DailyTransport"):
        create_transport(settings)


@pytest.mark.asyncio
async def test_create_transport_telnyx_raises() -> None:
    from src.config.settings import TelephonySettings

    settings = TelephonySettings(telephony_provider="telnyx")
    with pytest.raises(NotImplementedError, match="TelnyxTransport"):
        create_transport(settings)


@pytest.mark.asyncio
async def test_create_transport_unknown_provider_raises() -> None:
    """Unknown telephony provider should raise ValueError."""
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.telephony_provider = "unknown_provider"
    with pytest.raises(ValueError, match="Unknown telephony provider"):
        create_transport(settings)
