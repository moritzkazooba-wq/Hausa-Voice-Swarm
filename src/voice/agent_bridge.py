"""Agent bridge processor connecting Pipecat voice pipeline to LangGraph supervisor.

Receives TranscriptionFrame (ASR text), calls the LangGraph supervisor to
classify intent and route to a domain agent, then pushes the response as
a TextFrame for TTS synthesis.
"""

from __future__ import annotations

import time

import structlog
from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src.agents.intent import ClassificationResult
from src.agents.supervisor import route_to_agent
from src.metrics.definitions import voice_to_voice_latency_ms

logger = structlog.get_logger()


class AgentBridgeProcessor(FrameProcessor):
    """Bridge between Pipecat voice pipeline and LangGraph agent orchestrator.

    Intercepts TranscriptionFrame from ASR, calls the supervisor to classify
    intent and execute the domain agent, then pushes a TextFrame with the
    agent's response for TTS.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self._session_id = session_id
        self._last_classification: ClassificationResult | None = None

    @property
    def last_classification(self) -> ClassificationResult | None:
        """Most recent classification result (for API responses)."""
        return self._last_classification

    async def process_frame(
        self,
        frame: Frame,
        direction: FrameDirection,
    ) -> None:
        """Process incoming frames.

        On TranscriptionFrame: call LangGraph supervisor, push TextFrame.
        All other frames pass through unchanged.
        """
        if isinstance(frame, TranscriptionFrame):
            start = time.monotonic()

            result, classification = await route_to_agent(
                self._session_id,
                frame.text,
            )
            self._last_classification = classification

            elapsed_ms = (time.monotonic() - start) * 1000.0
            voice_to_voice_latency_ms.observe(elapsed_ms)

            await logger.ainfo(
                "agent_bridge_response",
                session_id=self._session_id,
                intent=classification.intent,
                confidence=classification.confidence,
                response=result.message,
                latency_ms=round(elapsed_ms, 1),
            )

            await self.push_frame(TextFrame(text=result.message))
        else:
            await self.push_frame(frame, direction)
