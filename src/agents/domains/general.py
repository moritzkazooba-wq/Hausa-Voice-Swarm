"""General inquiry agent — handles greetings, goodbyes, and FAQ."""

from __future__ import annotations

from src.agents.base import AgentResponse, BaseAgent
from src.models.session import AgentMessage, SessionState

GREETING_RESPONSES: dict[str, str] = {
    "greeting": "Sannu! Barka da zuwa. Yaya zan taimake ku yau?",
    "goodbye": "Na gode! Sai anjima. Allah ya kiyaye.",
}


class GeneralAgent(BaseAgent):
    """Handles greetings, goodbyes, and general FAQ. Uses Gemini Flash."""

    name = "general_agent"
    description = "Handles greetings, goodbyes, and general inquiries"
    model = "gemini-flash"

    async def handle(
        self,
        user_message: str,
        session: SessionState,
        history: list[AgentMessage],
    ) -> AgentResponse:
        """Return greeting/goodbye or general help response."""
        intent = session.current_intent

        if intent in GREETING_RESPONSES:
            return AgentResponse(message=GREETING_RESPONSES[intent])

        return AgentResponse(
            message=(
                "Zan iya taimaka muku da duba kuɗi, canja wuri, ko biyan lissafi. "
                "Me kuke bukata?"
            ),
        )
