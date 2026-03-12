"""Tests for VoiceMetrics model."""

from src.models.voice import VoiceMetrics


class TestVoiceMetrics:
    """VoiceMetrics validation tests."""

    def test_valid_metrics(self) -> None:
        metrics = VoiceMetrics(
            session_id="sess-001",
            v2v_latency_ms=450.5,
            asr_latency_ms=120.0,
            tts_latency_ms=80.3,
            llm_latency_ms=250.2,
            intent="balance_check",
            model_used="gemini-flash",
        )
        assert metrics.v2v_latency_ms == 450.5

    def test_serialization_roundtrip(self) -> None:
        metrics = VoiceMetrics(
            session_id="sess-002",
            v2v_latency_ms=300.0,
            asr_latency_ms=100.0,
            tts_latency_ms=50.0,
            llm_latency_ms=150.0,
            intent="transfer",
            model_used="gpt-4o",
        )
        json_str = metrics.model_dump_json()
        restored = VoiceMetrics.model_validate_json(json_str)
        assert restored == metrics
