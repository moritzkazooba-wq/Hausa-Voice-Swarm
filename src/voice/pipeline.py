"""Pipecat voice pipeline orchestration.

Constructs the voice pipeline:
  transport.input() → VAD → ASR → filler → agent_bridge → TTS → transport.output()
"""

from __future__ import annotations

from typing import Any

import structlog
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameProcessor

from src.config.settings import ASRSettings, TTSSettings
from src.metrics.definitions import active_voice_sessions
from src.voice.agent_bridge import AgentBridgeProcessor
from src.voice.asr import ASRManager, ASRProcessor
from src.voice.fillers import FillerProcessor
from src.voice.transport import StubTransport
from src.voice.tts import TTSManager, TTSProcessor
from src.voice.vad_config import create_vad_processor

logger = structlog.get_logger()


async def create_voice_pipeline(
    transport: StubTransport | Any,
    session_id: str,
    *,
    asr_settings: ASRSettings | None = None,
    tts_settings: TTSSettings | None = None,
    language: str = "ha",
) -> tuple[Pipeline, PipelineTask, AgentBridgeProcessor]:
    """Build the Pipecat voice pipeline for a session.

    Args:
        transport: Transport providing input/output processors.
        session_id: Unique session identifier.
        asr_settings: Optional ASR configuration override.
        tts_settings: Optional TTS configuration override.
        language: Language code for TTS routing (default "ha").

    Returns:
        A tuple of (pipeline, task, agent_bridge) so callers can access
        the bridge's classification result after pipeline completion.
    """
    agent_bridge = AgentBridgeProcessor(session_id)

    asr_manager = ASRManager(settings=asr_settings)
    tts_manager = TTSManager(settings=tts_settings)

    processors: list[FrameProcessor] = [
        transport.input(),
        create_vad_processor(),
        ASRProcessor(manager=asr_manager),
        FillerProcessor(),
        agent_bridge,
        TTSProcessor(manager=tts_manager, language=language),
        transport.output(),
    ]

    pipeline = Pipeline(processors)
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=False,
        ),
    )

    active_voice_sessions.inc()
    await logger.ainfo("voice_pipeline_created", session_id=session_id)

    return pipeline, task, agent_bridge
