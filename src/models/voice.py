"""Voice pipeline metrics model."""

from pydantic import BaseModel, ConfigDict


class VoiceMetrics(BaseModel):
    """Latency metrics for a single voice interaction."""

    model_config = ConfigDict(strict=True)

    session_id: str
    v2v_latency_ms: float
    asr_latency_ms: float
    tts_latency_ms: float
    llm_latency_ms: float
    intent: str
    model_used: str
