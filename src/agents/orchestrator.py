"""LangGraph-style supervisor — classifies intent and routes to domain agents."""

from __future__ import annotations

from datetime import UTC, datetime

from src.agents.base import AgentResponse, BaseAgent
from src.agents.domains.balance import BalanceAgent
from src.agents.domains.bills import BillPaymentAgent
from src.agents.domains.escalation import EscalationAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.technical import TechnicalAgent
from src.agents.domains.transfer import TransferAgent
from src.agents.intent import IntentResult, classify_intent
from src.models.session import AgentMessage, SessionState

# Confidence threshold — below this, escalate to human
CONFIDENCE_THRESHOLD: float = 0.5

# Map intents to agent classes
INTENT_AGENT_MAP: dict[str, type[BaseAgent]] = {
    "check_balance": BalanceAgent,
    "transfer_money": TransferAgent,
    "pay_bill": BillPaymentAgent,
    "pin_reset": TransferAgent,  # PIN reset uses same confirmation flow
    "technical_issue": TechnicalAgent,
    "speak_to_human": EscalationAgent,
    "greeting": GeneralAgent,
    "goodbye": GeneralAgent,
    "general": GeneralAgent,
}


class Supervisor:
    """Orchestrator that classifies intent and routes to the appropriate domain agent.

    Implements the orchestrator-worker pattern:
    1. Classify user intent
    2. Check confidence — escalate if too low
    3. Route to domain agent
    4. Return response with updated session state
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def _get_agent(self, agent_class: type[BaseAgent]) -> BaseAgent:
        """Get or create a cached agent instance."""
        name = agent_class.__name__
        if name not in self._agents:
            self._agents[name] = agent_class()
        return self._agents[name]

    async def route(
        self,
        user_message: str,
        session: SessionState,
    ) -> tuple[AgentResponse, SessionState]:
        """Classify intent and route to the appropriate domain agent.

        Returns the agent response and updated session state.
        """
        # 1. Classify intent
        intent_result: IntentResult = classify_intent(user_message)

        # 2. Update session with intent info
        session = session.model_copy(
            update={
                "current_intent": intent_result.intent,
                "confidence_history": [
                    *session.confidence_history,
                    intent_result.confidence,
                ],
            },
        )

        # 3. Check confidence — escalate if below threshold
        if intent_result.confidence < CONFIDENCE_THRESHOLD:
            agent = self._get_agent(EscalationAgent)
            session = session.model_copy(update={"current_agent": agent.name})
        else:
            agent_class = INTENT_AGENT_MAP.get(intent_result.intent, GeneralAgent)
            agent = self._get_agent(agent_class)
            session = session.model_copy(update={"current_agent": agent.name})

        # 4. Build conversation history
        user_msg = AgentMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(tz=UTC),
            agent_name="user",
        )
        history = [*session.conversation_turns, user_msg]

        # 5. Route to agent
        response = await agent.handle(user_message, session, history)

        # 6. Append assistant message to session
        assistant_msg = AgentMessage(
            role="assistant",
            content=response.message,
            timestamp=datetime.now(tz=UTC),
            agent_name=agent.name,
            metadata=response.metadata,
        )
        session = session.model_copy(
            update={
                "conversation_turns": [*history, assistant_msg],
            },
        )

        return response, session
