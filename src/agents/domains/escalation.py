"""Escalation agent — connects customers with human agents."""

from __future__ import annotations

from src.agents.base import AgentResponse, BaseAgent
from src.api.mock_resolvers import create_escalation_ticket
from src.models.session import AgentMessage, SessionState

# Mock estimated wait times by region
MOCK_WAIT_TIMES: dict[str, int] = {
    "kano": 5,
    "lagos": 12,
    "abuja": 8,
}
DEFAULT_WAIT_TIME: int = 10


class EscalationAgent(BaseAgent):
    """Handles escalation to human agents.

    Triggered by: speak_to_human intent, low confidence (< 0.5),
    or detected emotional distress. Uses GPT-4o.
    Creates an escalation ticket and provides estimated wait time.
    """

    name = "escalation_agent"
    description = "Escalates to human agent with ticket creation"
    model = "gpt-4o"

    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Create escalation ticket and provide wait time estimate."""
        issue = user_message if user_message else "Customer requested human agent"

        result = await create_escalation_ticket(
            phone_number=session.customer_phone,
            issue=issue,
        )

        region = getattr(session, "region", "kano") if hasattr(session, "region") else "kano"
        wait_time = MOCK_WAIT_TIMES.get(region, DEFAULT_WAIT_TIME)

        return AgentResponse(
            message=(
                f"Na ƙirƙiri tikiti don ku. "
                f"Za a haɗa ku da wakili a cikin mintuna {wait_time}."
            ),
            action_result=result,
            metadata={
                "wait_time_minutes": wait_time,
                "ticket_reference": result.reference_id,
                "escalation_reason": session.current_intent,
            },
        )
