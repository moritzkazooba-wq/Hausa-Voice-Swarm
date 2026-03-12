"""Balance inquiry agent — checks account balance via GraphQL."""

from __future__ import annotations

from src.agents.base import AgentResponse, BaseAgent
from src.api.mock_resolvers import get_customer
from src.models.session import AgentMessage, SessionState


class BalanceAgent(BaseAgent):
    """Handles balance check requests. Uses Gemini Flash (simple task)."""

    name = "balance_agent"
    description = "Checks account balance for customers"
    model = "gemini-flash"

    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Look up customer balance and return a short response."""
        customer = await get_customer(session.customer_phone)
        if customer is None:
            return AgentResponse(
                message="Ba mu sami asusun ku ba. Da fatan za a sake gwadawa.",
            )

        return AgentResponse(
            message=(
                f"Kudin ku shine {customer.currency} {customer.balance:,.2f}. "
                f"Shirin ku: {customer.plan}."
            ),
            metadata={"balance": str(customer.balance), "plan": customer.plan},
        )
