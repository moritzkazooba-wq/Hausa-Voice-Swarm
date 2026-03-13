"""General inquiry agent (FAQ, help) with LiteLLM integration."""

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult

_SYSTEM_PROMPT = (
    "You are a mobile money customer support agent for Hausa-speaking users. "
    "Respond in Hausa with English code-switching. Max 2 sentences. "
    "Answer general questions, provide help, or direct to appropriate services."
)


class GeneralAgent(BaseDomainAgent):
    """Handles general questions and FAQ."""

    agent_name: str = "general"
    complexity: str = "simple"

    def _mock_response(self, utterance: str) -> str:
        return "For help, please call our support line."

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        response = await self._call_llm(_SYSTEM_PROMPT, utterance)
        return ActionResult(success=True, message=response)
