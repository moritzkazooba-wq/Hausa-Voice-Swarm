"""Balance inquiry agent."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult


class BalanceAgent(BaseDomainAgent):
    """Handles balance inquiry requests."""

    agent_name: str = "balance"

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        # Mock implementation — real version queries account via repository
        return ActionResult(
            success=True,
            message="Your balance is 15,000 Naira.",
        )
