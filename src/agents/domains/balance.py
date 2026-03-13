"""Balance inquiry agent with LiteLLM integration."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult

_SYSTEM_PROMPT = (
    "You are a mobile money balance inquiry agent for Hausa-speaking users. "
    "Respond in Hausa with English code-switching. Max 2 sentences. "
    "Report the customer's balance clearly."
)


class BalanceAgent(BaseDomainAgent):
    """Handles balance inquiry requests."""

    agent_name: str = "balance"
    complexity: str = "simple"

    def _mock_response(self, utterance: str) -> str:
        return "Your balance is 15,000 Naira."

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        response = await self._call_llm(_SYSTEM_PROMPT, utterance)
        return ActionResult(success=True, message=response)
