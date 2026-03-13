"""Transport layer: StubTransport for testing, factory for provider selection.

StubTransport bypasses real audio: injects text as TranscriptionFrame via
PipelineTask.queue_frame() and captures TextFrame output via asyncio.Event.
"""

from __future__ import annotations

import asyncio

import structlog
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    StartFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.config.settings import TelephonySettings

logger = structlog.get_logger()


class StubInputTransport(FrameProcessor):
    """Passthrough processor at the pipeline head for stub transport.

    Frame injection is handled externally via PipelineTask.queue_frame().
    This processor simply passes all frames downstream unchanged.
    Sets a ``pipeline_ready`` event when StartFrame is received.
    """

    def __init__(self, pipeline_ready: asyncio.Event | None = None) -> None:
        super().__init__()
        self._pipeline_ready = pipeline_ready

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Pass all frames through; signal readiness on StartFrame."""
        if isinstance(frame, StartFrame) and self._pipeline_ready is not None:
            self._pipeline_ready.set()
        await self.push_frame(frame, direction)


class StubOutputTransport(FrameProcessor):
    """Captures TextFrame content for test assertions.

    Sets ``response_ready`` event when the first TextFrame is received.
    Collected text is available via ``collected_text`` property.
    """

    def __init__(self) -> None:
        super().__init__()
        self._collected: list[str] = []
        self.response_ready = asyncio.Event()

    @property
    def collected_text(self) -> str:
        """All captured response text joined."""
        return " ".join(self._collected)

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Capture TextFrame content, pass everything through."""
        if isinstance(frame, TextFrame):
            self._collected.append(frame.text)
            if not self.response_ready.is_set():
                self.response_ready.set()

        await self.push_frame(frame, direction)


class StubTransport:
    """Text-in / text-out transport for testing without real audio.

    Usage::

        transport = StubTransport("Ina so in duba balance dina")
        pipeline, task, bridge = await create_voice_pipeline(transport, sid)
        runner = PipelineRunner()
        run_task = asyncio.create_task(runner.run(task))
        await transport.inject_text(task)  # queue frames into running pipeline
        await transport.response_ready.wait()
        print(transport.collected_text)
    """

    def __init__(self, input_text: str) -> None:
        self._input_text = input_text
        self._pipeline_ready = asyncio.Event()
        self._input_proc = StubInputTransport(pipeline_ready=self._pipeline_ready)
        self._output_proc = StubOutputTransport()

    def input(self) -> FrameProcessor:
        """Input processor for pipeline head."""
        return self._input_proc

    def output(self) -> FrameProcessor:
        """Output processor for pipeline tail."""
        return self._output_proc

    @property
    def response_ready(self) -> asyncio.Event:
        """Event set when the first response TextFrame is captured."""
        return self._output_proc.response_ready

    @property
    def collected_text(self) -> str:
        """All captured response text."""
        return self._output_proc.collected_text

    async def inject_text(self, task: object) -> None:
        """Inject the input text into the running pipeline via task.queue_frame.

        Must be called after the pipeline runner has started the task.
        Waits briefly for pipeline startup, then queues the TranscriptionFrame.
        """
        from pipecat.pipeline.task import PipelineTask

        assert isinstance(task, PipelineTask)

        # Wait for pipeline to signal readiness via StartFrame
        await asyncio.wait_for(self._pipeline_ready.wait(), timeout=5.0)

        await task.queue_frame(
            TranscriptionFrame(
                text=self._input_text,
                user_id="stub-caller",
                timestamp="0",
            ),
        )
        # Queue EndFrame to signal pipeline completion after processing
        await task.queue_frame(EndFrame())


def create_transport(
    settings: TelephonySettings | None = None,
    *,
    input_text: str = "",
) -> StubTransport:
    """Factory: create a transport based on telephony provider config.

    Currently only ``stub`` provider is implemented. Daily and Telnyx
    transports are placeholders for future phases.
    """
    cfg = settings or TelephonySettings()

    if cfg.telephony_provider == "stub":
        return StubTransport(input_text)

    if cfg.telephony_provider == "daily":
        raise NotImplementedError(
            "DailyTransport not yet implemented. "
            "Set TELEPHONY_PROVIDER=stub for development."
        )

    if cfg.telephony_provider == "telnyx":
        raise NotImplementedError(
            "TelnyxTransport not yet implemented. "
            "Set TELEPHONY_PROVIDER=stub for development. "
            "Activate with TELEPHONY_PROVIDER=telnyx + credentials."
        )

    msg = f"Unknown telephony provider: {cfg.telephony_provider}"
    raise ValueError(msg)
