"""Money transfer agent (requires confirmation)."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult


class TransferAgent(BaseDomainAgent):
    """Handles money transfer requests. Always requires confirmation."""

    agent_name: str = "transfer"

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        return ActionResult(
            success=True,
            message="Transfer of 5,000 Naira ready. Please confirm.",
            requires_confirmation=True,
        )
