"""Base agent interface for domain agents with Prometheus instrumentation."""

from __future__ import annotations

import abc
import time
from typing import TYPE_CHECKING

import structlog

from src.metrics.definitions import tool_execution_total
from src.models.transaction import ActionResult

if TYPE_CHECKING:
    from src.db.repositories import CustomerRepository
    from src.db.session_store import SessionStore

logger = structlog.get_logger()


class BaseDomainAgent(abc.ABC):
    """Abstract base class for domain agents (balance, transfer, bills, general).

    Subclasses implement ``_execute`` with their domain logic.
    The public ``run`` method handles timing, metrics, and logging.

    Optional ``session_store`` and ``customer_repo`` can be injected for
    agents that need session context or customer data.
    """

    agent_name: str = "base"

    def __init__(
        self,
        session_store: SessionStore | None = None,
        customer_repo: CustomerRepository | None = None,
    ) -> None:
        self.session_store = session_store
        self.customer_repo = customer_repo

    @abc.abstractmethod
    async def _execute(
        self,
        session_id: str,
        utterance: str,
    ) -> ActionResult:
        """Domain-specific logic. Subclasses must implement."""
        ...

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
