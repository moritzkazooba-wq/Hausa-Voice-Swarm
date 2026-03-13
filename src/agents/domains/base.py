"""Base agent interface for domain agents with LiteLLM and Prometheus instrumentation."""

from __future__ import annotations

import abc
import time

import structlog

from src.metrics.definitions import llm_latency_ms, tool_execution_total
from src.models.transaction import ActionResult

logger = structlog.get_logger()


class BaseDomainAgent(abc.ABC):
    """Abstract base class for domain agents (balance, transfer, bills, general).

    Subclasses implement ``_execute`` with their domain logic and provide
    a ``_mock_response`` for MOCK_LLM mode.  The public ``run`` method
    handles timing, metrics, and logging.
    """

    agent_name: str = "base"
    # Subclasses override: "simple" uses default_model, "complex" uses complex_model
    complexity: str = "simple"

    @abc.abstractmethod
    async def _execute(
        self,
        session_id: str,
        utterance: str,
    ) -> ActionResult:
        """Domain-specific logic. Subclasses must implement."""
        ...

    async def _call_llm(
        self,
        system_prompt: str,
        utterance: str,
    ) -> str:
        """Call LiteLLM with mock/real toggle.

        When ``MOCK_LLM=true`` (default), returns a canned response without
        making any API calls.  When ``MOCK_LLM=false``, calls
        ``litellm.acompletion`` with cost-aware model routing.
        """
        from src.config.settings import AppSettings, LLMSettings

        app_settings = AppSettings()
        llm_settings = LLMSettings()

        if app_settings.mock_llm:
            return self._mock_response(utterance)

        import litellm

        model = (
            llm_settings.complex_model
            if self.complexity == "complex"
            else llm_settings.default_model
        )

        start = time.monotonic()
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": utterance},
            ],
            max_tokens=150,
        )
        elapsed = (time.monotonic() - start) * 1000.0
        llm_latency_ms.labels(model=model, intent=self.agent_name).observe(elapsed)

        return response.choices[0].message.content or self._mock_response(utterance)

    def _mock_response(self, utterance: str) -> str:
        """Default mock response. Subclasses should override."""
        return "Request processed."

    async def run(
        self,
        session_id: str,
        utterance: str,
    ) -> ActionResult:
        """Execute the agent with metrics instrumentation."""
        start = time.monotonic()
        result = await self._execute(session_id, utterance)
        elapsed_ms = (time.monotonic() - start) * 1000.0

        tool_execution_total.labels(
            tool_name=self.agent_name,
            success=str(result.success),
        ).inc()

        await logger.ainfo(
            "agent_executed",
            agent_name=self.agent_name,
            session_id=session_id,
            success=result.success,
            elapsed_ms=elapsed_ms,
        )

        return result
