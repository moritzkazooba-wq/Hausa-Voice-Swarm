"""Balance inquiry and account info agent (stub)."""

from datetime import UTC, datetime
from typing import Any

from src.agents.base import BaseAgent
from src.models.session import AgentMessage

RESPONSES: dict[str, str] = {
    "ha": "Kuɗin ku ya kai N15,000.50. Akwai wani abin da kuke bukata?",
    "en": "Your balance is N15,000.50. Is there anything else you need?",
    "pcm": "Your balance na N15,000.50. You need anything else?",
}


class BalanceAgent(BaseAgent):
    """Handles balance inquiries and account information."""

    name = "balance_agent"
    description = "Handles balance inquiries and account info"

    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a placeholder balance response."""
        lang = state.get("language", "en")
        response = RESPONSES.get(lang, RESPONSES["en"])
        return {
            "current_agent": self.name,
            "response": response,
            "messages": [
                AgentMessage(
                    role="assistant",
                    content=response,
                    timestamp=datetime.now(UTC),
                    agent_name=self.name,
                ),
            ],
        }
