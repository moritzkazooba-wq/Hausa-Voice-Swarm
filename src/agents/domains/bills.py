"""Bill payment agent (requires confirmation)."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult


class BillsAgent(BaseDomainAgent):
    """Handles bill payment requests. Always requires confirmation."""

    agent_name: str = "bills"

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        return ActionResult(
            success=True,
            message="Bill payment of 3,000 Naira ready. Please confirm.",
            requires_confirmation=True,
        )
