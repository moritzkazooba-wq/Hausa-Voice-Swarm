"""Money transfer agent (requires confirmation) with LiteLLM integration."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult

_SYSTEM_PROMPT = (
    "You are a mobile money transfer agent for Hausa-speaking users. "
    "Respond in Hausa with English code-switching. Max 2 sentences. "
    "Confirm transfer details and ask the user to verify before proceeding."
)


class TransferAgent(BaseDomainAgent):
    """Handles money transfer requests. Always requires confirmation."""

    agent_name: str = "transfer"
    complexity: str = "complex"

    def _mock_response(self, utterance: str) -> str:
        return "Transfer of 5,000 Naira ready. Please confirm."

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        response = await self._call_llm(_SYSTEM_PROMPT, utterance)
        return ActionResult(
            success=True,
            message=response,
            requires_confirmation=True,
        )
