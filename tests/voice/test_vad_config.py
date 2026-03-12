"""Tests for Silero VAD configuration."""

from __future__ import annotations

from pipecat.processors.audio.vad_processor import VADProcessor
from src.voice.vad_config import create_vad_params, create_vad_processor


def test_create_vad_processor_returns_frame_processor() -> None:
    processor = create_vad_processor()
    assert isinstance(processor, VADProcessor)


def test_vad_params_match_spec() -> None:
    params = create_vad_params()
    assert params.confidence == 0.5
    assert params.start_secs == 0.3
    assert params.stop_secs == 0.8
    assert params.min_volume == 0.6
