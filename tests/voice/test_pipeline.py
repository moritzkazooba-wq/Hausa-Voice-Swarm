"""Tests for voice pipeline construction."""

from __future__ import annotations

import pytest
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from src.voice.agent_bridge import AgentBridgeProcessor
from src.voice.pipeline import create_voice_pipeline
from src.voice.transport import StubTransport


@pytest.mark.asyncio
async def test_create_voice_pipeline_returns_tuple() -> None:
    transport = StubTransport("test input")
    pipeline, task, bridge = await create_voice_pipeline(transport, "sess-1")
    assert isinstance(pipeline, Pipeline)
    assert isinstance(task, PipelineTask)
    assert isinstance(bridge, AgentBridgeProcessor)


@pytest.mark.asyncio
async def test_pipeline_has_correct_processor_count() -> None:
    transport = StubTransport("test")
    pipeline, _task, _bridge = await create_voice_pipeline(transport, "sess-2")
    # 7 user processors + 2 internal (Pipeline Source + Sink) = 9
    assert len(pipeline._processors) == 9  # type: ignore[attr-defined]
