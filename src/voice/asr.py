"""ASR processors (Intron/Whisper-Hausa stub fallback).

Stub processor simulates transcription with configurable latency.
Real Intron API integration is activated via USE_REAL_ASR=true.
"""

from __future__ import annotations

import asyncio
import time

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


class StubASRProcessor(FrameProcessor):
    """Stub ASR that converts audio frames into transcription frames.

    In stub mode (default), simulates ASR by forwarding text already set
    via ``set_text()`` or a default canned response after a simulated delay.
    """

    def __init__(
        self,
        *,
        settings: ASRSettings | None = None,
        stub_latency_ms: float = 100.0,
    ) -> None:
        super().__init__()
        self._settings = settings or ASRSettings()
        self._stub_latency_ms = stub_latency_ms
        self._pending_text: str | None = None

    def set_text(self, text: str) -> None:
        """Pre-load text for stub transcription (used by StubTransport)."""
        self._pending_text = text

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Process incoming frames.

        On InputAudioRawFrame: simulate ASR and emit TranscriptionFrame.
        All other frames pass through unchanged.
        """
        if isinstance(frame, InputAudioRawFrame):
            start = time.monotonic()
            await asyncio.sleep(self._stub_latency_ms / 1000.0)
            elapsed_ms = (time.monotonic() - start) * 1000.0

            text = self._pending_text or "Ina so in biya kuɗi"
            self._pending_text = None

            asr_latency_ms.labels(model="stub", intent="unknown").observe(
                elapsed_ms,
            )
            await logger.ainfo(
                "asr_transcribed",
                text=text,
                latency_ms=round(elapsed_ms, 1),
                model="stub",
            )

            await self.push_frame(
                TranscriptionFrame(
                    text=text,
                    user_id="caller",
                    timestamp=str(time.time()),
                ),
            )
        else:
            await self.push_frame(frame, direction)
