"""Technical issue agent — diagnoses network/service problems with step-by-step guidance."""

from __future__ import annotations

from src.agents.base import AgentResponse, BaseAgent
from src.api.mock_resolvers import get_network_status
from src.models.session import AgentMessage, SessionState


class TechnicalAgent(BaseAgent):
    """Handles technical issues: network problems, errors, service outages.

    Uses GPT-4o for complex diagnostics. Asks clarifying questions,
    checks network status, and provides step-by-step guidance.
    """

    name = "technical_agent"
    description = "Diagnoses technical issues and provides troubleshooting guidance"
    model = "gpt-4o"

    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Diagnose technical issue — check network status, provide guidance."""
        network = await get_network_status(session.region if hasattr(session, "region") else "kano")

        if network is None:
            return AgentResponse(
                message=(
                    "Muna duba matsalar ku. Don Allah ku sake gwadawa bayan mintuna biyar."
                ),
                metadata={"network_status": "unknown"},
            )

        if network.status == "down":
            return AgentResponse(
                message=(
                    f"Hanyar sadarwa a {network.region} ba ta aiki yanzu. "
                    "Muna gyara matsalar, don Allah ku jira."
                ),
                metadata={
                    "network_status": network.status,
                    "region": network.region,
                    "latency_ms": network.latency_ms,
                },
            )

        if network.status == "degraded":
            return AgentResponse(
                message=(
                    f"Hanyar sadarwa a {network.region} tana jinkiri ({network.latency_ms:.0f}ms). "
                    "Ku sake gwadawa a hankali."
                ),
                metadata={
                    "network_status": network.status,
                    "region": network.region,
                    "latency_ms": network.latency_ms,
                },
            )

        # Network is healthy — ask clarifying question
        return AgentResponse(
            message=(
                "Hanyar sadarwa tana aiki daidai. Wace irin matsala kuke fuskanta? "
                "Misali: biyan kuɗi bai yi nasara ba, ko wani abu dabam?"
            ),
            metadata={
                "network_status": network.status,
                "region": network.region,
                "latency_ms": network.latency_ms,
                "step": "clarifying_question",
            },
        )
