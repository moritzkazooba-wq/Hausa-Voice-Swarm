"""Tests for TTS providers, language-aware manager, and processor."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pipecat.frames.frames import (
    Frame,
    OutputAudioRawFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from src.voice.tts import (
    _SILENT_AUDIO,
    CartesiaTTS,
    IntronTTS,
    TTSManager,
    TTSProcessor,
    TTSProvider,
)

# ── Provider tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_intron_tts_stub_returns_audio() -> None:
    """IntronTTS stub returns silent audio bytes."""
    provider = IntronTTS()
    audio = await provider.synthesize("Sannu")
    assert isinstance(audio, bytes)
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_intron_tts_stub_latency_range() -> None:
    """IntronTTS stub latency is within 150-300ms range."""
    import time

    provider = IntronTTS()
    start = time.monotonic()
    await provider.synthesize("Sannu")
    elapsed_ms = (time.monotonic() - start) * 1000.0
    assert elapsed_ms >= 130.0
    assert elapsed_ms < 400.0


@pytest.mark.asyncio
async def test_intron_tts_name_and_languages() -> None:
    provider = IntronTTS()
    assert provider.name == "intron"
    assert "ha" in provider.supported_languages


@pytest.mark.asyncio
async def test_cartesia_tts_stub_returns_audio() -> None:
    """CartesiaTTS stub returns silent audio bytes."""
    provider = CartesiaTTS()
    audio = await provider.synthesize("Hello")
    assert isinstance(audio, bytes)
    assert len(audio) > 0


@pytest.mark.asyncio
async def test_cartesia_tts_stub_latency_range() -> None:
    """CartesiaTTS stub latency is within 100-250ms range."""
    import time

    provider = CartesiaTTS()
    start = time.monotonic()
    await provider.synthesize("Hello")
    elapsed_ms = (time.monotonic() - start) * 1000.0
    assert elapsed_ms >= 80.0
    assert elapsed_ms < 350.0


@pytest.mark.asyncio
async def test_cartesia_tts_name_and_languages() -> None:
    provider = CartesiaTTS()
    assert provider.name == "cartesia"
    assert "en" in provider.supported_languages
    assert "pcm" in provider.supported_languages


@pytest.mark.asyncio
async def test_tts_provider_protocol() -> None:
    """Both providers satisfy the TTSProvider protocol."""
    assert isinstance(IntronTTS(), TTSProvider)
    assert isinstance(CartesiaTTS(), TTSProvider)


# ── Manager language routing tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_manager_routes_ha_to_intron() -> None:
    """TTSManager routes 'ha' to IntronTTS."""
    intron = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    intron.name = "intron"
    intron.supported_languages = ["ha"]
    intron.synthesize = AsyncMock(return_value=_SILENT_AUDIO)

    cartesia = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    cartesia.name = "cartesia"
    cartesia.supported_languages = ["en", "pcm"]

    manager = TTSManager(intron=intron, cartesia=cartesia)
    _audio, provider_name = await manager.synthesize(
        "Sannu", language="ha",
    )

    assert provider_name == "intron"
    intron.synthesize.assert_awaited_once_with("Sannu")
    cartesia.synthesize.assert_not_called()


@pytest.mark.asyncio
async def test_manager_routes_en_to_cartesia() -> None:
    """TTSManager routes 'en' to CartesiaTTS."""
    intron = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    intron.name = "intron"
    intron.supported_languages = ["ha"]

    cartesia = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    cartesia.name = "cartesia"
    cartesia.supported_languages = ["en", "pcm"]
    cartesia.synthesize = AsyncMock(return_value=_SILENT_AUDIO)

    manager = TTSManager(intron=intron, cartesia=cartesia)
    _audio, provider_name = await manager.synthesize(
        "Hello", language="en",
    )

    assert provider_name == "cartesia"
    cartesia.synthesize.assert_awaited_once_with("Hello")
    intron.synthesize.assert_not_called()


@pytest.mark.asyncio
async def test_manager_routes_pcm_to_cartesia() -> None:
    """TTSManager routes 'pcm' to CartesiaTTS."""
    cartesia = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    cartesia.name = "cartesia"
    cartesia.supported_languages = ["en", "pcm"]
    cartesia.synthesize = AsyncMock(return_value=_SILENT_AUDIO)

    manager = TTSManager(cartesia=cartesia)
    _audio, provider_name = await manager.synthesize(
        "Wetin dey", language="pcm",
    )

    assert provider_name == "cartesia"


@pytest.mark.asyncio
async def test_manager_raises_for_unsupported_language() -> None:
    """TTSManager raises ValueError for unsupported language."""
    manager = TTSManager()

    with pytest.raises(ValueError, match="No TTS provider for language 'fr'"):
        await manager.synthesize("Bonjour", language="fr")


@pytest.mark.asyncio
async def test_manager_provider_for_returns_correct_provider() -> None:
    """TTSManager.provider_for returns the mapped provider."""
    manager = TTSManager()
    ha_provider = manager.provider_for("ha")
    assert ha_provider.name == "intron"

    en_provider = manager.provider_for("en")
    assert en_provider.name == "cartesia"


@pytest.mark.asyncio
async def test_manager_records_tts_latency_metric() -> None:
    """TTSManager records tts_latency_ms on success."""
    intron = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    intron.name = "intron"
    intron.supported_languages = ["ha"]
    intron.synthesize = AsyncMock(return_value=_SILENT_AUDIO)

    manager = TTSManager(intron=intron)

    with patch("src.voice.tts.tts_latency_ms") as mock_metric:
        mock_labels = AsyncMock()
        mock_metric.labels.return_value = mock_labels
        await manager.synthesize("test", language="ha")
        mock_metric.labels.assert_called_with(model="intron", intent="unknown")
        mock_labels.observe.assert_called_once()


# ── Processor tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_processor_synthesizes_text_frame() -> None:
    """TTSProcessor converts TextFrame to TextFrame + OutputAudioRawFrame."""
    intron = AsyncMock(spec=["name", "supported_languages", "synthesize"])
    intron.name = "intron"
    intron.supported_languages = ["ha"]
    intron.synthesize = AsyncMock(return_value=_SILENT_AUDIO)

    manager = TTSManager(intron=intron)
    proc = TTSProcessor(manager=manager, language="ha")

    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    proc.push_frame = capture  # type: ignore[assignment]

    await proc.process_frame(TextFrame(text="Sannu"), FrameDirection.DOWNSTREAM)

    assert len(pushed) == 2
    assert isinstance(pushed[0], TextFrame)
    assert pushed[0].text == "Sannu"
    assert isinstance(pushed[1], OutputAudioRawFrame)


@pytest.mark.asyncio
async def test_processor_passes_through_other_frames() -> None:
    """TTSProcessor passes non-TextFrame through unchanged."""
    proc = TTSProcessor()

    pushed: list[Frame] = []

    async def capture(frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM) -> None:
        pushed.append(frame)

    proc.push_frame = capture  # type: ignore[assignment]

    tf = TranscriptionFrame(text="pass", user_id="u1", timestamp="0")
    await proc.process_frame(tf, FrameDirection.DOWNSTREAM)

    assert len(pushed) == 1
    assert pushed[0] is tf


# ── End-to-end text → ASR → agent → TTS → text ────────────────────


@pytest.mark.asyncio
async def test_end_to_end_text_through_pipeline_components() -> None:
    """Text flows through ASR processor → agent bridge → TTS processor."""
    from pipecat.frames.frames import InputAudioRawFrame
    from src.models.transaction import ActionResult
    from src.voice.agent_bridge import AgentBridgeProcessor
    from src.voice.asr import ASRManager, ASRProcessor

    # Set up ASR processor with mock manager
    asr_primary = AsyncMock(spec=["name", "transcribe"])
    asr_primary.name = "mock-asr"
    asr_primary.transcribe = AsyncMock(
        return_value="Ina so in duba balance",
    )
    asr_manager = ASRManager(primary=asr_primary)
    asr_proc = ASRProcessor(manager=asr_manager)

    # Set up agent bridge
    bridge = AgentBridgeProcessor(session_id="e2e-test")

    # Set up TTS processor with mock manager
    tts_intron = AsyncMock(
        spec=["name", "supported_languages", "synthesize"],
    )
    tts_intron.name = "intron"
    tts_intron.supported_languages = ["ha"]
    tts_intron.synthesize = AsyncMock(return_value=_SILENT_AUDIO)
    tts_manager = TTSManager(intron=tts_intron)
    tts_proc = TTSProcessor(manager=tts_manager, language="ha")

    # Wire: ASR output → bridge, bridge output → TTS
    bridge_pushed: list[Frame] = []
    tts_pushed: list[Frame] = []

    async def bridge_capture(
        frame: Frame,
        direction: FrameDirection = FrameDirection.DOWNSTREAM,
    ) -> None:
        bridge_pushed.append(frame)
        if isinstance(frame, TextFrame):
            await tts_proc.process_frame(frame, direction)

    async def tts_capture(
        frame: Frame,
        direction: FrameDirection = FrameDirection.DOWNSTREAM,
    ) -> None:
        tts_pushed.append(frame)

    async def asr_to_bridge(
        frame: Frame,
        direction: FrameDirection = FrameDirection.DOWNSTREAM,
    ) -> None:
        if isinstance(frame, TranscriptionFrame):
            await bridge.process_frame(frame, direction)

    asr_proc.push_frame = asr_to_bridge  # type: ignore[assignment]
    bridge.push_frame = bridge_capture  # type: ignore[assignment]
    tts_proc.push_frame = tts_capture  # type: ignore[assignment]

    # Mock the agent supervisor
    mock_result = ActionResult(
        success=True, message="Your balance is 5,000 NGN.",
    )
    mock_classification = AsyncMock()
    mock_classification.intent = "balance"
    mock_classification.confidence = 0.95

    with patch(
        "src.voice.agent_bridge.route_to_agent",
        return_value=(mock_result, mock_classification),
    ):
        audio_frame = InputAudioRawFrame(
            audio=b"\x00" * 160,
            sample_rate=16000,
            num_channels=1,
        )
        await asr_proc.process_frame(
            audio_frame, FrameDirection.DOWNSTREAM,
        )

    # Verify the full chain executed
    assert len(bridge_pushed) == 1
    assert isinstance(bridge_pushed[0], TextFrame)
    assert bridge_pushed[0].text == "Your balance is 5,000 NGN."

    assert len(tts_pushed) == 2
    assert isinstance(tts_pushed[0], TextFrame)
    assert isinstance(tts_pushed[1], OutputAudioRawFrame)
