"""Bill payment and plan change agent (stub, requires confirmation)."""

from datetime import UTC, datetime
from typing import Any

from src.agents.base import BaseAgent
from src.models.session import AgentMessage

RESPONSES: dict[str, str] = {
    "ha": "Za mu sarrafa biyan ku. Da fatan za a tabbatar da adadin da hanyar biyan.",
    "en": "We'll process your payment. Please confirm the amount and payment method.",
    "pcm": "We go process your payment. Abeg confirm the amount and how you wan pay.",
}


class BillsAgent(BaseAgent):
    """Handles bill payments and plan changes (requires confirmation)."""

    name = "bills_agent"
    description = "Handles payments and plan changes"

    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a placeholder payment response."""
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
