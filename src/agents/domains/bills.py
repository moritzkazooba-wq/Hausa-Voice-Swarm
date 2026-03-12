"""Bill payment agent — handles bill payments with confirmation."""

from __future__ import annotations

from src.agents.base import AgentResponse, BaseAgent
from src.api.mock_resolvers import process_payment
from src.models.session import AgentMessage, SessionState


class BillPaymentAgent(BaseAgent):
    """Handles bill payments (airtime, DSTV, electricity). Uses GPT-4o."""

    name = "bill_payment_agent"
    description = "Processes bill payments and subscriptions"
    model = "gpt-4o"

    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Process bill payment — always requires confirmation first."""
        result = await process_payment(
            phone_number=session.customer_phone,
            amount=0.0,
            merchant="bill_payment",
        )
        return AgentResponse(
            message="Mun sami buƙatar biyan ku. Don Allah ku tabbatar da biyan.",
            action_result=result,
            metadata={"requires_confirmation": True},
        )
