"""Silero VAD configuration for voice activity detection."""

from __future__ import annotations

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.audio.vad_processor import VADProcessor


def create_vad_params() -> VADParams:
    """Return project-tuned VAD parameters.

    Parameters:
        confidence=0.5  — detection threshold (lower = more sensitive)
        start_secs=0.3  — 300ms pad before SPEAKING state
        stop_secs=0.8   — 800ms silence before QUIET (endpointing)
        min_volume=0.6  — minimum audio volume threshold
    """
    return VADParams(
        confidence=0.5,
        start_secs=0.3,
        stop_secs=0.8,
        min_volume=0.6,
    )


def create_vad_processor() -> VADProcessor:
    """Create a VADProcessor wrapping Silero VAD with project-tuned params."""
    analyzer = SileroVADAnalyzer(params=create_vad_params())
    return VADProcessor(vad_analyzer=analyzer)
