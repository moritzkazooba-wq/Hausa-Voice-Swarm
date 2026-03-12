"""TTS processors (Intron/Cartesia stub fallback).

Stub processor simulates speech synthesis with configurable latency.
Real Intron/Cartesia API integration is activated via USE_REAL_TTS=true.
"""

from __future__ import annotations

import asyncio
import time

import structlog
from pipecat.frames.frames import (
    Frame,
    OutputAudioRawFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.config.settings import TTSSettings
from src.metrics.definitions import tts_latency_ms

logger = structlog.get_logger()

# 160 bytes of silence (10ms of 16kHz 16-bit mono PCM)
_SILENT_AUDIO = b"\x00" * 160


class StubTTSProcessor(FrameProcessor):
    """Stub TTS that converts text frames into silent audio frames.

    In stub mode (default), simulates TTS by emitting silent audio after
    a configurable delay. Real TTS produces actual Hausa speech audio.
    """

    def __init__(
        self,
        *,
        settings: TTSSettings | None = None,
        stub_latency_ms: float = 150.0,
    ) -> None:
        super().__init__()
        self._settings = settings or TTSSettings()
        self._stub_latency_ms = stub_latency_ms

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Process incoming frames.

        On TextFrame: simulate TTS and emit OutputAudioRawFrame with silence.
        All other frames pass through unchanged.
        """
        if isinstance(frame, TextFrame):
            start = time.monotonic()
            await asyncio.sleep(self._stub_latency_ms / 1000.0)
            elapsed_ms = (time.monotonic() - start) * 1000.0

            tts_latency_ms.labels(model="stub", intent="unknown").observe(
                elapsed_ms,
            )
            await logger.ainfo(
                "tts_synthesized",
                text=frame.text,
                latency_ms=round(elapsed_ms, 1),
                model="stub",
            )

            # Forward the TextFrame so downstream can capture the text
            await self.push_frame(frame, direction)
            # Then push synthesized (silent) audio
            await self.push_frame(
                OutputAudioRawFrame(
                    audio=_SILENT_AUDIO,
                    sample_rate=16000,
                    num_channels=1,
                ),
            )
        else:
            await self.push_frame(frame, direction)
