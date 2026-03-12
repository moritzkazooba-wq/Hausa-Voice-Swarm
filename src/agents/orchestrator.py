"""LangGraph StateGraph supervisor — routes to domain agents."""

import operator
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from src.agents.base import BaseAgent
from src.agents.domains.balance import BalanceAgent
from src.agents.domains.bills import BillsAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.transfer import TransferAgent
from src.agents.intent import IntentClassifier, IntentResult
from src.models.session import AgentMessage

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Supervisor state — shared memory for all graph nodes
# ---------------------------------------------------------------------------

# Per LangGraph fundamentals: use Annotated[list, operator.add] for append-only
# "without a reducer, returning a list overwrites previous values"


class SupervisorState(TypedDict):
    """Shared state passed through the supervisor graph."""

    messages: Annotated[list[AgentMessage], operator.add]
    language: str
    intent: str
    confidence: float
    customer_context: dict[str, Any]
    current_agent: str
    session_id: str
    response: str


# ---------------------------------------------------------------------------
# Intent → domain agent mapping
# ---------------------------------------------------------------------------

INTENT_AGENT_MAP: dict[str, str] = {
    "balance_check": "balance",
    "account_info": "balance",
    "transaction_history": "balance",
    "payment": "bills",
    "plan_change": "bills",
    "pin_reset": "transfer",
    "dispute": "general",
    "technical_issue": "general",
    "other": "general",
}

DOMAIN_AGENTS: dict[str, BaseAgent] = {
    "balance": BalanceAgent(),
    "transfer": TransferAgent(),
    "bills": BillsAgent(),
    "general": GeneralAgent(),
}

# ---------------------------------------------------------------------------
# Greeting responses (max 2 sentences, per cross-cutting rules)
# ---------------------------------------------------------------------------

GREETING_RESPONSES: dict[str, str] = {
    "ha": "Sannu da zuwa! Yaya za mu taimake ku yau?",
    "en": "Welcome! How can we help you today?",
    "pcm": "Welcome o! How we fit help you today?",
}

ESCALATION_RESPONSES: dict[str, str] = {
    "ha": "Za mu haɗa ku da wakili a yanzu. Da fatan za a jira.",
    "en": "We're connecting you to a human agent now. Please hold.",
    "pcm": "We dey connect you to person now. Abeg hold on.",
}


# ---------------------------------------------------------------------------
# Graph node functions
# Per LangGraph skill: "Return partial update dictionaries only —
# never mutate and return full state objects."
# ---------------------------------------------------------------------------


def _make_classify_node(
    classifier: IntentClassifier,
) -> Any:
    """Create the classify_intent node function with a bound classifier."""

    async def classify_intent(state: SupervisorState) -> dict[str, Any]:
        """Classify the user's most recent message."""
        user_text = ""
        for msg in reversed(state["messages"]):
            if msg.role == "user":
                user_text = msg.content
                break

        result: IntentResult = await classifier.classify(user_text)
        logger.info(
            "supervisor.classified",
            intent=result.intent,
            confidence=result.confidence,
            classifier=result.classifier_type,
            latency_ms=result.latency_ms,
        )
        return {
            "intent": result.intent,
            "confidence": result.confidence,
        }

    return classify_intent


def route_intent(state: SupervisorState) -> Literal["greeting", "escalation", "domain"]:
    """Route based on classified intent and confidence.

    Per LangGraph skill: use Literal types for routing targets.
    """
    if state["confidence"] < 0.5 or state["intent"] == "speak_to_human":
        return "escalation"
    if state["intent"] == "greeting":
        return "greeting"
    return "domain"


async def greeting_node(state: SupervisorState) -> dict[str, Any]:
    """Handle greeting — respond directly without a domain agent."""
    lang = state.get("language", "en")
    response = GREETING_RESPONSES.get(lang, GREETING_RESPONSES["en"])
    return {
        "current_agent": "supervisor",
        "response": response,
        "messages": [
            AgentMessage(
                role="assistant",
                content=response,
                timestamp=datetime.now(UTC),
                agent_name="supervisor",
            ),
        ],
    }


async def escalation_node(state: SupervisorState) -> dict[str, Any]:
    """Escalate to a human agent."""
    lang = state.get("language", "en")
    response = ESCALATION_RESPONSES.get(lang, ESCALATION_RESPONSES["en"])
    logger.info(
        "supervisor.escalation",
        reason="low_confidence" if state["confidence"] < 0.5 else "user_request",
        intent=state["intent"],
    )
    return {
        "current_agent": "human",
        "response": response,
        "messages": [
            AgentMessage(
                role="assistant",
                content=response,
                timestamp=datetime.now(UTC),
                agent_name="supervisor",
            ),
        ],
    }


async def domain_node(state: SupervisorState) -> dict[str, Any]:
    """Dispatch to the appropriate domain agent based on intent."""
    agent_key = INTENT_AGENT_MAP.get(state["intent"], "general")
    agent = DOMAIN_AGENTS[agent_key]
    logger.debug(
        "supervisor.domain_dispatch",
        intent=state["intent"],
        agent=agent.name,
    )
    return await agent.handle(dict(state))


# ---------------------------------------------------------------------------
# Graph builder
# Per LangGraph skill: "add nodes before referencing in edges"
# Per LangGraph skill: "must compile() before invoke()"
# ---------------------------------------------------------------------------


def build_supervisor(classifier: IntentClassifier) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and compile the supervisor StateGraph.

    Graph flow:
        START → classify_intent → route_intent → [greeting | escalation | domain] → END
    """
    graph = StateGraph(SupervisorState)

    # Add ALL nodes first (per LangGraph skill)
    graph.add_node("classify_intent", _make_classify_node(classifier))
    graph.add_node("greeting", greeting_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("domain", domain_node)

    # Then edges
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {"greeting": "greeting", "escalation": "escalation", "domain": "domain"},
    )
    graph.add_edge("greeting", END)
    graph.add_edge("escalation", END)
    graph.add_edge("domain", END)

    return graph.compile()
