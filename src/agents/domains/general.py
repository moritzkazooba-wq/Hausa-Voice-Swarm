"""General inquiry agent (FAQ, help)."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult


class GeneralAgent(BaseDomainAgent):
    """Handles general questions and FAQ."""

    agent_name: str = "general"

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        return ActionResult(
            success=True,
            message="For help, please call our support line.",
        )
