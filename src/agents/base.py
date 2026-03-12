"""Base agent interface for domain agents."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all domain agents."""

    name: str
    description: str

    @abstractmethod
    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process the user request and return partial state updates.

        Per LangGraph conventions, returns only the fields that changed —
        never the full state object.
        """
        ...
