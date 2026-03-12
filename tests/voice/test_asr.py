"""Tests for ASR providers, manager fallback, and processor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from src.config.settings import ASRSettings
from src.voice.asr import (
    ASRManager,
    ASRProcessor,
    ASRProvider,
    IntronASR,
    WhisperASR,
)

# ── Provider tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_intron_asr_stub_returns_text() -> None:
    """IntronASR stub returns canned text after simulated latency."""
    provider = IntronASR()
    text = await provider.transcribe(b"\x00" * 160)
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.asyncio
async def test_intron_asr_stub_latency_range() -> None:
    """IntronASR stub latency is within 200-400ms range."""
    import time

    provider = IntronASR()
    start = time.monotonic()
    await provider.transcribe(b"\x00" * 160)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    # Allow margin for scheduling
    assert elapsed_ms >= 180.0
    assert elapsed_ms < 500.0


@pytest.mark.asyncio
async def test_intron_asr_set_stub_text() -> None:
    """IntronASR.set_stub_text pre-loads custom text."""
    provider = IntronASR()
    provider.set_stub_text("custom text")
    text = await provider.transcribe(b"\x00" * 160)
    assert text == "custom text"


@pytest.mark.asyncio
async def test_intron_asr_name() -> None:
    assert IntronASR().name == "intron"


@pytest.mark.asyncio
async def test_whisper_asr_stub_returns_text() -> None:
    """WhisperASR stub returns canned text after simulated latency."""
    provider = WhisperASR()
    text = await provider.transcribe(b"\x00" * 160)
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.asyncio
async def test_whisper_asr_stub_latency_range() -> None:
    """WhisperASR stub latency is within 300-600ms range."""
    import time

    provider = WhisperASR()
    start = time.monotonic()
    await provider.transcribe(b"\x00" * 160)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    assert elapsed_ms >= 280.0
    assert elapsed_ms < 700.0


@pytest.mark.asyncio
async def test_whisper_asr_name() -> None:
    assert WhisperASR().name == "whisper"


@pytest.mark.asyncio
async def test_asr_provider_protocol() -> None:
    """Both providers satisfy the ASRProvider protocol."""
    assert isinstance(IntronASR(), ASRProvider)
    assert isinstance(WhisperASR(), ASRProvider)


# ── Manager fallback tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_manager_uses_primary_on_success() -> None:
    """ASRManager uses primary provider when it succeeds."""
    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "mock-primary"
    primary.transcribe = AsyncMock(return_value="primary result")

    fallback = AsyncMock(spec=["name", "transcribe"])
    fallback.name = "mock-fallback"

    manager = ASRManager(primary=primary, fallback=fallback)
    text, provider_name = await manager.transcribe(b"\x00")

    assert text == "primary result"
    assert provider_name == "mock-primary"
    primary.transcribe.assert_awaited_once_with(b"\x00")
    fallback.transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_manager_falls_back_on_primary_failure() -> None:
    """ASRManager falls back when primary raises an exception."""
    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "mock-primary"
    primary.transcribe = AsyncMock(side_effect=RuntimeError("API error"))

    fallback = AsyncMock(spec=["name", "transcribe"])
    fallback.name = "mock-fallback"
    fallback.transcribe = AsyncMock(return_value="fallback result")

    settings = ASRSettings(asr_fallback_enabled=True)
    manager = ASRManager(primary=primary, fallback=fallback, settings=settings)
    text, provider_name = await manager.transcribe(b"\x00")

    assert text == "fallback result"
    assert provider_name == "mock-fallback"


@pytest.mark.asyncio
async def test_manager_falls_back_on_primary_timeout() -> None:
    """ASRManager falls back when primary exceeds timeout."""

    async def slow_transcribe(_audio: bytes) -> str:
        await asyncio.sleep(5.0)
        return "too late"

    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "mock-primary"
    primary.transcribe = slow_transcribe

    fallback = AsyncMock(spec=["name", "transcribe"])
    fallback.name = "mock-fallback"
    fallback.transcribe = AsyncMock(return_value="fallback result")

    settings = ASRSettings(asr_timeout_seconds=0.1, asr_fallback_enabled=True)
    manager = ASRManager(primary=primary, fallback=fallback, settings=settings)
    text, provider_name = await manager.transcribe(b"\x00")

    assert text == "fallback result"
    assert provider_name == "mock-fallback"


@pytest.mark.asyncio
async def test_manager_raises_when_fallback_disabled() -> None:
    """ASRManager raises when fallback is disabled and primary fails."""
    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "mock-primary"
    primary.transcribe = AsyncMock(side_effect=RuntimeError("fail"))

    fallback = AsyncMock(spec=["name", "transcribe"])
    fallback.name = "mock-fallback"

    settings = ASRSettings(asr_fallback_enabled=False, asr_timeout_seconds=2.0)
    manager = ASRManager(primary=primary, fallback=fallback, settings=settings)

    with pytest.raises(RuntimeError, match="fail"):
        await manager.transcribe(b"\x00")


@pytest.mark.asyncio
async def test_manager_raises_when_both_fail() -> None:
    """ASRManager raises when both primary and fallback fail."""
    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "mock-primary"
    primary.transcribe = AsyncMock(side_effect=RuntimeError("primary fail"))

    fallback = AsyncMock(spec=["name", "transcribe"])
    fallback.name = "mock-fallback"
    fallback.transcribe = AsyncMock(side_effect=RuntimeError("fallback fail"))

    settings = ASRSettings(asr_fallback_enabled=True, asr_timeout_seconds=2.0)
    manager = ASRManager(primary=primary, fallback=fallback, settings=settings)

    with pytest.raises(RuntimeError, match="fallback fail"):
        await manager.transcribe(b"\x00")


@pytest.mark.asyncio
async def test_manager_records_asr_latency_metric() -> None:
    """ASRManager records asr_latency_ms on success."""
    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "test-provider"
    primary.transcribe = AsyncMock(return_value="text")

    manager = ASRManager(primary=primary)

    with patch("src.voice.asr.asr_latency_ms") as mock_metric:
        mock_labels = AsyncMock()
        mock_metric.labels.return_value = mock_labels
        await manager.transcribe(b"\x00")
        mock_metric.labels.assert_called_with(model="test-provider", intent="unknown")
        mock_labels.observe.assert_called_once()


# ── Processor tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_processor_transcribes_audio_frame() -> None:
    """ASRProcessor converts InputAudioRawFrame to TranscriptionFrame."""
    primary = AsyncMock(spec=["name", "transcribe"])
    primary.name = "mock"
    primary.transcribe = AsyncMock(return_value="hello world")

    manager = ASRManager(primary=primary)
    proc = ASRProcessor(manager=manager)

    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    proc.push_frame = capture  # type: ignore[assignment]

    audio_frame = InputAudioRawFrame(audio=b"\x00" * 160, sample_rate=16000, num_channels=1)
    await proc.process_frame(audio_frame, FrameDirection.DOWNSTREAM)

    assert len(pushed) == 1
    assert isinstance(pushed[0], TranscriptionFrame)
    assert pushed[0].text == "hello world"


@pytest.mark.asyncio
async def test_processor_passes_through_transcription_frame() -> None:
    """ASRProcessor passes through existing TranscriptionFrame."""
    proc = ASRProcessor()

    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    proc.push_frame = capture  # type: ignore[assignment]

    tf = TranscriptionFrame(text="passthrough", user_id="u1", timestamp="0")
    await proc.process_frame(tf, FrameDirection.DOWNSTREAM)

    assert len(pushed) == 1
    assert pushed[0] is tf


@pytest.mark.asyncio
async def test_processor_passes_through_other_frames() -> None:
    """ASRProcessor passes through non-audio, non-transcription frames."""
    proc = ASRProcessor()

    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    proc.push_frame = capture  # type: ignore[assignment]

    text_frame = TextFrame(text="hello")
    await proc.process_frame(text_frame, FrameDirection.DOWNSTREAM)

    assert len(pushed) == 1
    assert pushed[0] is text_frame
