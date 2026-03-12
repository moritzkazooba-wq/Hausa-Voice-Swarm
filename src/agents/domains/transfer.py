"""Money transfer and PIN reset agent (stub, requires confirmation)."""

from datetime import UTC, datetime
from typing import Any

from src.agents.base import BaseAgent
from src.models.session import AgentMessage

RESPONSES: dict[str, str] = {
    "ha": "Don sake saita PIN ɗinku, za mu aika lambar tabbatarwa. Shin kun yarda?",
    "en": "To reset your PIN, we'll send a verification code. Do you confirm?",
    "pcm": "To reset your PIN, we go send verification code. You agree?",
}


class TransferAgent(BaseAgent):
    """Handles money transfers and PIN resets (requires confirmation)."""

    name = "transfer_agent"
    description = "Handles transfers and security operations"

    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a placeholder transfer/PIN response."""
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
