"""Base agent interface for domain agents."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from src.models.session import AgentMessage, SessionState
from src.models.transaction import ActionResult


@dataclass
class AgentResponse:
    """Response from a domain agent."""

    message: str
    action_result: ActionResult | None = None
    route_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(abc.ABC):
    """Abstract base class for all domain agents.

    Each domain agent handles a specific intent category and produces
    short (max 2 sentence) responses suitable for low-literacy users.
    """

    name: str
    description: str
    model: str  # LiteLLM model identifier

    @abc.abstractmethod
    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Process user message and return a response."""

    async def _mock_llm_response(self, prompt: str) -> str:
        """Return a deterministic mock LLM response for testing."""
        return f"[mock-{self.name}] {prompt[:80]}"
