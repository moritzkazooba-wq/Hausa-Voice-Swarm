"""Silero VAD configuration (re-exports from vad_config)."""

from src.voice.vad_config import create_vad_params, create_vad_processor

__all__ = ["create_vad_params", "create_vad_processor"]
