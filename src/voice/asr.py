"""ASR provider protocol, stub/real implementations, and fallback manager.

ASRProvider protocol with IntronASR and WhisperASR implementations.
ASRManager: primary → fallback on failure or timeout >2s.
Stub mode (default) simulates latency; real HTTP when USE_REAL_ASR=true.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Protocol, runtime_checkable

import structlog
from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.config.settings import ASRSettings
from src.metrics.definitions import asr_latency_ms

logger = structlog.get_logger()


@runtime_checkable
class ASRProvider(Protocol):
    """Protocol for ASR provider implementations."""

    @property
    def name(self) -> str:
        """Provider name for metrics and logging."""
        ...

    async def transcribe(self, audio: bytes) -> str:
        """Transcribe audio bytes to text.

        Raises:
            Exception: On transcription failure.
        """
        ...


class IntronASR:
    """Intron ASR provider — Hausa-optimised speech recognition.

    Stub mode: returns canned text after 200-400ms simulated latency.
    Real mode (USE_REAL_ASR=true): sends audio to Intron HTTP API.
    """

    def __init__(self, *, settings: ASRSettings | None = None) -> None:
        self._settings = settings or ASRSettings()
        self._stub_text: str | None = None

    @property
    def name(self) -> str:
        return "intron"

    def set_stub_text(self, text: str) -> None:
        """Pre-load text for stub transcription (testing)."""
        self._stub_text = text

    async def transcribe(self, audio: bytes) -> str:
        """Transcribe audio via Intron API or stub."""
        if self._settings.use_real_asr:
            return await self._real_transcribe(audio)
        return await self._stub_transcribe()

    async def _stub_transcribe(self) -> str:
        latency = random.uniform(200.0, 400.0)  # noqa: S311
        await asyncio.sleep(latency / 1000.0)
        text = self._stub_text or "Ina so in duba balance dina"
        self._stub_text = None
        return text

    async def _real_transcribe(self, audio: bytes) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=self._settings.asr_timeout_seconds) as client:
            resp = await client.post(
                self._settings.intron_asr_url,
                headers={"Authorization": f"Bearer {self._settings.intron_api_key}"},
                content=audio,
            )
            resp.raise_for_status()
            data = resp.json()
        return str(data.get("text", ""))


class WhisperASR:
    """Whisper ASR provider — uses Project A fine-tuned Hausa model.

    Stub mode: returns canned text after 300-600ms simulated latency.
    Real mode: loads model from whisper_model_path (future integration).
    """

    def __init__(self, *, settings: ASRSettings | None = None) -> None:
        self._settings = settings or ASRSettings()
        self._stub_text: str | None = None

    @property
    def name(self) -> str:
        return "whisper"

    def set_stub_text(self, text: str) -> None:
        """Pre-load text for stub transcription (testing)."""
        self._stub_text = text

    async def transcribe(self, audio: bytes) -> str:
        """Transcribe audio via Whisper model or stub."""
        if self._settings.use_real_asr and self._settings.whisper_model_path:
            return await self._real_transcribe(audio)
        return await self._stub_transcribe()

    async def _stub_transcribe(self) -> str:
        latency = random.uniform(300.0, 600.0)  # noqa: S311
        await asyncio.sleep(latency / 1000.0)
        text = self._stub_text or "Ina so in biya kuɗi"
        self._stub_text = None
        return text

    async def _real_transcribe(self, audio: bytes) -> str:
        raise NotImplementedError(
            f"Whisper model loading not yet implemented. "
            f"Model path: {self._settings.whisper_model_path}"
        )


class ASRManager:
    """Manages ASR with primary → fallback on failure or timeout.

    Uses the configured primary provider first. On failure or timeout (>2s),
    falls back to the secondary provider.
    """

    def __init__(
        self,
        *,
        primary: ASRProvider | None = None,
        fallback: ASRProvider | None = None,
        settings: ASRSettings | None = None,
    ) -> None:
        self._settings = settings or ASRSettings()
        self._primary = primary or IntronASR(settings=self._settings)
        self._fallback = fallback or WhisperASR(settings=self._settings)
        self._timeout = self._settings.asr_timeout_seconds
        self._fallback_enabled = self._settings.asr_fallback_enabled

    @property
    def primary(self) -> ASRProvider:
        return self._primary

    @property
    def fallback(self) -> ASRProvider:
        return self._fallback

    async def transcribe(self, audio: bytes) -> tuple[str, str]:
        """Transcribe audio with fallback.

        Returns:
            Tuple of (transcribed_text, provider_name).
        """
        start = time.monotonic()

        try:
            text = await asyncio.wait_for(
                self._primary.transcribe(audio),
                timeout=self._timeout,
            )
            elapsed_ms = (time.monotonic() - start) * 1000.0
            asr_latency_ms.labels(model=self._primary.name, intent="unknown").observe(
                elapsed_ms,
            )
            await logger.ainfo(
                "asr_transcribed",
                text=text,
                provider=self._primary.name,
                latency_ms=round(elapsed_ms, 1),
            )
            return text, self._primary.name

        except (TimeoutError, Exception) as exc:
            primary_elapsed = (time.monotonic() - start) * 1000.0
            await logger.awarning(
                "asr_primary_failed",
                provider=self._primary.name,
                error=str(exc),
                elapsed_ms=round(primary_elapsed, 1),
            )

            if not self._fallback_enabled:
                raise

            return await self._try_fallback(audio)

    async def _try_fallback(self, audio: bytes) -> tuple[str, str]:
        """Attempt transcription with the fallback provider."""
        start = time.monotonic()
        try:
            text = await asyncio.wait_for(
                self._fallback.transcribe(audio),
                timeout=self._timeout,
            )
            elapsed_ms = (time.monotonic() - start) * 1000.0
            asr_latency_ms.labels(
                model=self._fallback.name, intent="unknown",
            ).observe(elapsed_ms)
            await logger.ainfo(
                "asr_fallback_succeeded",
                text=text,
                provider=self._fallback.name,
                latency_ms=round(elapsed_ms, 1),
            )
            return text, self._fallback.name
        except (TimeoutError, Exception) as exc:
            await logger.aerror(
                "asr_fallback_failed",
                provider=self._fallback.name,
                error=str(exc),
            )
            raise


class ASRProcessor(FrameProcessor):
    """Pipecat FrameProcessor that uses ASRManager for transcription.

    On InputAudioRawFrame: transcribes via ASRManager, emits TranscriptionFrame.
    On TranscriptionFrame: passes through (from StubTransport).
    All other frames pass through unchanged.
    """

    def __init__(
        self,
        *,
        manager: ASRManager | None = None,
        settings: ASRSettings | None = None,
    ) -> None:
        super().__init__()
        self._manager = manager or ASRManager(settings=settings)

    @property
    def manager(self) -> ASRManager:
        return self._manager

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Process incoming frames."""
        if isinstance(frame, InputAudioRawFrame):
            text, _provider = await self._manager.transcribe(frame.audio)
            await self.push_frame(
                TranscriptionFrame(
                    text=text,
                    user_id="caller",
                    timestamp=str(time.time()),
                ),
            )
        elif isinstance(frame, TranscriptionFrame):
            # Pass through TranscriptionFrames from StubTransport
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)


# Keep backward compat alias
StubASRProcessor = ASRProcessor
