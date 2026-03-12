"""General inquiry, dispute, and technical issue agent (stub)."""

from datetime import UTC, datetime
from typing import Any

from src.agents.base import BaseAgent
from src.models.session import AgentMessage

RESPONSES: dict[str, str] = {
    "ha": "Mun karɓi tambayar ku. Za mu bincika kuma mu amsa a nan gaba.",
    "en": "We've received your inquiry. We'll investigate and respond shortly.",
    "pcm": "We don receive your question. We go check am and get back to you.",
}


class GeneralAgent(BaseAgent):
    """Handles general inquiries, disputes, and technical issues."""

    name = "general_agent"
    description = "Handles general inquiries, disputes, and technical issues"

    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a placeholder general response."""
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
