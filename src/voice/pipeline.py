"""Pipecat voice pipeline orchestration.

Constructs the voice pipeline:
  transport.input() → VAD → ASR → filler → agent_bridge → TTS → transport.output()
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import structlog
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameProcessor

from src.metrics.definitions import active_voice_sessions
from src.voice.agent_bridge import AgentBridgeProcessor
from src.voice.asr import StubASRProcessor
from src.voice.fillers import FillerProcessor
from src.voice.tts import StubTTSProcessor
from src.voice.vad_config import create_vad_processor

logger = structlog.get_logger()


@runtime_checkable
class TransportProtocol(Protocol):
    """Protocol for voice transports (stub, Daily, Telnyx)."""

    def input(self) -> FrameProcessor: ...
    def output(self) -> FrameProcessor: ...


async def create_voice_pipeline(
    transport: TransportProtocol,
    session_id: str,
) -> tuple[Pipeline, PipelineTask, AgentBridgeProcessor]:
    """Build the Pipecat voice pipeline for a session.

    Returns:
        A tuple of (pipeline, task, agent_bridge) so callers can access
        the bridge's classification result after pipeline completion.
    """
    agent_bridge = AgentBridgeProcessor(session_id)

    processors: list[FrameProcessor] = [
        transport.input(),
        create_vad_processor(),
        StubASRProcessor(),
        FillerProcessor(),
        agent_bridge,
        StubTTSProcessor(),
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
