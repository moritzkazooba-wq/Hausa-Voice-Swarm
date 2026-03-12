"""TTS provider protocol, stub/real implementations, and language-aware manager.

TTSProvider protocol with IntronTTS (Hausa) and CartesiaTTS (English).
TTSManager: routes "ha" → Intron, "en"/"pcm" → Cartesia.
Stub mode (default) simulates latency; real HTTP when USE_REAL_TTS=true.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Protocol, runtime_checkable

import structlog
from pipecat.frames.frames import (
    Frame,
    OutputAudioRawFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.config.settings import TTSSettings
from src.metrics.definitions import tts_latency_ms

logger = structlog.get_logger()

# 160 bytes of silence (10ms of 16kHz 16-bit mono PCM)
_SILENT_AUDIO = b"\x00" * 160


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for TTS provider implementations."""

    @property
    def name(self) -> str:
        """Provider name for metrics and logging."""
        ...

    @property
    def supported_languages(self) -> list[str]:
        """Language codes this provider supports."""
        ...

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio bytes (16kHz 16-bit mono PCM).

        Raises:
            Exception: On synthesis failure.
        """
        ...


class IntronTTS:
    """Intron TTS provider — Hausa speech synthesis.

    Stub mode: returns silent audio after 150-300ms simulated latency.
    Real mode (USE_REAL_TTS=true): sends text to Intron HTTP API.
    """

    def __init__(self, *, settings: TTSSettings | None = None) -> None:
        self._settings = settings or TTSSettings()

    @property
    def name(self) -> str:
        return "intron"

    @property
    def supported_languages(self) -> list[str]:
        return ["ha"]

    async def synthesize(self, text: str) -> bytes:
        """Synthesize Hausa text to audio."""
        if self._settings.use_real_tts:
            return await self._real_synthesize(text)
        return await self._stub_synthesize()

    async def _stub_synthesize(self) -> bytes:
        latency = random.uniform(150.0, 300.0)  # noqa: S311
        await asyncio.sleep(latency / 1000.0)
        return _SILENT_AUDIO

    async def _real_synthesize(self, text: str) -> bytes:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                self._settings.intron_tts_url,
                headers={"Authorization": f"Bearer {self._settings.intron_api_key}"},
                json={"text": text, "language": "ha"},
            )
            resp.raise_for_status()
        return resp.content


class CartesiaTTS:
    """Cartesia TTS provider — English and PCM speech synthesis.

    Stub mode: returns silent audio after 100-250ms simulated latency.
    Real mode (USE_REAL_TTS=true): sends text to Cartesia HTTP API.
    """

    def __init__(self, *, settings: TTSSettings | None = None) -> None:
        self._settings = settings or TTSSettings()

    @property
    def name(self) -> str:
        return "cartesia"

    @property
    def supported_languages(self) -> list[str]:
        return ["en", "pcm"]

    async def synthesize(self, text: str) -> bytes:
        """Synthesize English/PCM text to audio."""
        if self._settings.use_real_tts:
            return await self._real_synthesize(text)
        return await self._stub_synthesize()

    async def _stub_synthesize(self) -> bytes:
        latency = random.uniform(100.0, 250.0)  # noqa: S311
        await asyncio.sleep(latency / 1000.0)
        return _SILENT_AUDIO

    async def _real_synthesize(self, text: str) -> bytes:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                self._settings.cartesia_tts_url,
                headers={"X-API-Key": self._settings.cartesia_api_key},
                json={
                    "transcript": text,
                    "model_id": "sonic-english",
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": 16000,
                    },
                },
            )
            resp.raise_for_status()
        return resp.content


class TTSManager:
    """Language-aware TTS routing: "ha" → Intron, "en"/"pcm" → Cartesia.

    Records tts_latency_ms per provider.
    """

    def __init__(
        self,
        *,
        settings: TTSSettings | None = None,
        intron: IntronTTS | None = None,
        cartesia: CartesiaTTS | None = None,
    ) -> None:
        self._settings = settings or TTSSettings()
        self._intron = intron or IntronTTS(settings=self._settings)
        self._cartesia = cartesia or CartesiaTTS(settings=self._settings)
        self._providers: dict[str, TTSProvider] = {
            "ha": self._intron,
            "en": self._cartesia,
            "pcm": self._cartesia,
        }

    @property
    def intron(self) -> IntronTTS:
        return self._intron

    @property
    def cartesia(self) -> CartesiaTTS:
        return self._cartesia

    def provider_for(self, language: str) -> TTSProvider:
        """Get the TTS provider for a language code.

        Raises:
            ValueError: If no provider supports the language.
        """
        provider = self._providers.get(language)
        if provider is None:
            msg = (
                f"No TTS provider for language '{language}'. "
                f"Supported: {list(self._providers.keys())}"
            )
            raise ValueError(msg)
        return provider

    async def synthesize(self, text: str, *, language: str = "ha") -> tuple[bytes, str]:
        """Synthesize text to audio with language-based routing.

        Returns:
            Tuple of (audio_bytes, provider_name).
        """
        provider = self.provider_for(language)
        start = time.monotonic()

        audio = await provider.synthesize(text)

        elapsed_ms = (time.monotonic() - start) * 1000.0
        tts_latency_ms.labels(model=provider.name, intent="unknown").observe(
            elapsed_ms,
        )
        await logger.ainfo(
            "tts_synthesized",
            text=text[:50],
            provider=provider.name,
            language=language,
            latency_ms=round(elapsed_ms, 1),
        )
        return audio, provider.name


class TTSProcessor(FrameProcessor):
    """Pipecat FrameProcessor that uses TTSManager for synthesis.

    On TextFrame: synthesizes via TTSManager, pushes TextFrame through
    (for downstream capture) then pushes OutputAudioRawFrame.
    All other frames pass through unchanged.
    """

    def __init__(
        self,
        *,
        manager: TTSManager | None = None,
        settings: TTSSettings | None = None,
        language: str = "ha",
    ) -> None:
        super().__init__()
        self._manager = manager or TTSManager(settings=settings)
        self._language = language

    @property
    def manager(self) -> TTSManager:
        return self._manager

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Process incoming frames."""
        if isinstance(frame, TranscriptionFrame):
            # TranscriptionFrame is a TextFrame subclass — pass through
            await self.push_frame(frame, direction)
        elif isinstance(frame, TextFrame):
            audio, _provider = await self._manager.synthesize(
                frame.text, language=self._language,
            )

            # Forward TextFrame so downstream (StubOutputTransport) can capture text
            await self.push_frame(frame, direction)
            # Then push synthesized audio
            await self.push_frame(
                OutputAudioRawFrame(
                    audio=audio,
                    sample_rate=16000,
                    num_channels=1,
                ),
            )
        else:
            await self.push_frame(frame, direction)


# Keep backward compat alias
StubTTSProcessor = TTSProcessor
