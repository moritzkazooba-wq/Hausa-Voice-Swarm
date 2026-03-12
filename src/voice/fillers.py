"""Filler audio processor for latency masking.

Triggers filler audio when response latency exceeds 500ms to
mask processing delay for the user. Currently logs the trigger;
actual filler audio playback deferred to real TTS integration.
"""

from __future__ import annotations

import time

import structlog
from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = structlog.get_logger()

FILLER_THRESHOLD_MS: float = 500.0


class FillerProcessor(FrameProcessor):
    """Monitors latency between ASR and response; triggers filler if >500ms.

    Tracks time from TranscriptionFrame arrival to first TextFrame. If
    the elapsed time exceeds ``FILLER_THRESHOLD_MS``, logs a filler trigger
    (placeholder for actual filler audio injection).
    """

    def __init__(self) -> None:
        super().__init__()
        self._speech_start: float | None = None
        self._filler_triggered = False

    @property
    def filler_was_triggered(self) -> bool:
        """Whether a filler was triggered in this session (for testing)."""
        return self._filler_triggered

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Track latency and trigger filler when threshold exceeded."""
        if isinstance(frame, TranscriptionFrame):
            self._speech_start = time.monotonic()
            self._filler_triggered = False

        elif isinstance(frame, TextFrame) and self._speech_start is not None:
            elapsed_ms = (time.monotonic() - self._speech_start) * 1000.0
            if elapsed_ms > FILLER_THRESHOLD_MS:
                self._filler_triggered = True
                await logger.ainfo(
                    "filler_triggered",
                    elapsed_ms=round(elapsed_ms, 1),
                    threshold_ms=FILLER_THRESHOLD_MS,
                )
            self._speech_start = None

        await self.push_frame(frame, direction)
