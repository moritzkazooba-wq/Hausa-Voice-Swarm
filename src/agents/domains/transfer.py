"""Money transfer agent — processes transfers with confirmation."""

from __future__ import annotations

from src.agents.base import AgentResponse, BaseAgent
from src.api.mock_resolvers import process_payment
from src.models.session import AgentMessage, SessionState


class TransferAgent(BaseAgent):
    """Handles money transfers. Uses GPT-4o (complex financial task)."""

    name = "transfer_agent"
    description = "Processes money transfers between accounts"
    model = "gpt-4o"

    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Process transfer request — always requires confirmation first."""
        result = await process_payment(
            phone_number=session.customer_phone,
            amount=0.0,
            merchant="transfer",
        )
        return AgentResponse(
            message="Don Allah ku tabbatar da canja wurin kuɗi. Shin kuna so ku ci gaba?",
            action_result=result,
            metadata={"requires_confirmation": True},
        )
