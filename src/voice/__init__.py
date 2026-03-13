"""Voice pipeline: Pipecat transport → VAD → ASR → agent bridge → TTS → output."""

from src.voice.agent_bridge import AgentBridgeProcessor
from src.voice.asr import StubASRProcessor
from src.voice.fillers import FillerProcessor
from src.voice.pipeline import create_voice_pipeline
from src.voice.transport import StubTransport, create_transport
from src.voice.tts import StubTTSProcessor
from src.voice.vad_config import create_vad_params, create_vad_processor

__all__ = [
    "AgentBridgeProcessor",
    "FillerProcessor",
    "StubASRProcessor",
    "StubTTSProcessor",
    "StubTransport",
    "create_transport",
    "create_vad_params",
    "create_vad_processor",
    "create_voice_pipeline",
]
