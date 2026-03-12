"""Tests for LangGraph supervisor orchestrator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from src.agents.intent import IntentClassifier, IntentResult
from src.agents.orchestrator import (
    GREETING_RESPONSES,
    SupervisorState,
    build_supervisor,
    route_intent,
)
from src.models.session import AgentMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    text: str = "hello",
    language: str = "en",
    intent: str = "",
    confidence: float = 0.0,
) -> SupervisorState:
    """Build a minimal SupervisorState for testing."""
    return SupervisorState(
        messages=[
            AgentMessage(
                role="user",
                content=text,
                timestamp=datetime.now(UTC),
                agent_name="user",
            ),
        ],
        language=language,
        intent=intent,
        confidence=confidence,
        customer_context={},
        current_agent="",
        session_id="test-session",
        response="",
    )


def _mock_classifier(intent: str, confidence: float) -> IntentClassifier:
    """Create a mock IntentClassifier returning a fixed result."""
    clf = IntentClassifier.__new__(IntentClassifier)
    clf._model = None
    clf._centroids = {}
    clf._ready = True

    async def mock_classify(text: str) -> IntentResult:
        return IntentResult(
            intent=intent,
            confidence=confidence,
            classifier_type="embedding",
            latency_ms=10.0,
        )

    clf.classify = mock_classify  # type: ignore[assignment]
    return clf


# ---------------------------------------------------------------------------
# route_intent unit tests
# ---------------------------------------------------------------------------


class TestRouteIntent:
    def test_greeting(self) -> None:
        state = _make_state(intent="greeting", confidence=0.9)
        assert route_intent(state) == "greeting"

    def test_escalation_low_confidence(self) -> None:
        state = _make_state(intent="balance_check", confidence=0.3)
        assert route_intent(state) == "escalation"

    def test_escalation_speak_to_human(self) -> None:
        state = _make_state(intent="speak_to_human", confidence=0.9)
        assert route_intent(state) == "escalation"

    def test_domain_routing(self) -> None:
        state = _make_state(intent="balance_check", confidence=0.85)
        assert route_intent(state) == "domain"

    def test_domain_dispute(self) -> None:
        state = _make_state(intent="dispute", confidence=0.75)
        assert route_intent(state) == "domain"


# ---------------------------------------------------------------------------
# Full graph execution tests
# ---------------------------------------------------------------------------


class TestSupervisor:
    async def test_build_supervisor_returns_compiled(self) -> None:
        clf = _mock_classifier("greeting", 0.9)
        graph = build_supervisor(clf)
        assert graph is not None

    async def test_greeting_bypass(self) -> None:
        """Greeting intent should be handled directly, not by domain agent."""
        clf = _mock_classifier("greeting", 0.9)
        graph = build_supervisor(clf)
        state = _make_state("Sannu", language="ha")
        result = await graph.ainvoke(state)
        assert result["current_agent"] == "supervisor"
        assert result["intent"] == "greeting"

    async def test_greeting_hausa_response(self) -> None:
        """Hausa greeting should respond in Hausa."""
        clf = _mock_classifier("greeting", 0.9)
        graph = build_supervisor(clf)
        state = _make_state("Sannu", language="ha")
        result = await graph.ainvoke(state)
        assert result["response"] == GREETING_RESPONSES["ha"]

    async def test_greeting_english_response(self) -> None:
        clf = _mock_classifier("greeting", 0.95)
        graph = build_supervisor(clf)
        state = _make_state("Hello", language="en")
        result = await graph.ainvoke(state)
        assert result["response"] == GREETING_RESPONSES["en"]

    async def test_escalation_low_confidence(self) -> None:
        """Low confidence should escalate to human."""
        clf = _mock_classifier("balance_check", 0.3)
        graph = build_supervisor(clf)
        state = _make_state("mumble mumble", language="en")
        result = await graph.ainvoke(state)
        assert result["current_agent"] == "human"

    async def test_escalation_speak_to_human(self) -> None:
        clf = _mock_classifier("speak_to_human", 0.9)
        graph = build_supervisor(clf)
        state = _make_state("I want to talk to a person", language="en")
        result = await graph.ainvoke(state)
        assert result["current_agent"] == "human"

    async def test_domain_balance(self) -> None:
        """balance_check routes to billing agent."""
        clf = _mock_classifier("balance_check", 0.85)
        graph = build_supervisor(clf)
        state = _make_state("Check my balance", language="en")
        with patch(
            "src.agents.domains.billing.BillingAgent.handle",
            new_callable=AsyncMock,
            return_value={
                "current_agent": "billing_agent",
                "response": "Your balance is N15,000.50.",
                "messages": [],
            },
        ):
            result = await graph.ainvoke(state)
        assert result["current_agent"] == "billing_agent"

    async def test_domain_payment(self) -> None:
        """payment routes to billing agent."""
        clf = _mock_classifier("payment", 0.8)
        graph = build_supervisor(clf)
        state = _make_state("Pay my bill", language="en")
        with patch(
            "src.agents.domains.billing.BillingAgent.handle",
            new_callable=AsyncMock,
            return_value={
                "current_agent": "billing_agent",
                "response": "We will process your payment.",
                "messages": [],
            },
        ):
            result = await graph.ainvoke(state)
        assert result["current_agent"] == "billing_agent"

    async def test_domain_dispute(self) -> None:
        """dispute routes to billing agent."""
        clf = _mock_classifier("dispute", 0.75)
        graph = build_supervisor(clf)
        state = _make_state("I have a dispute", language="en")
        with patch(
            "src.agents.domains.billing.BillingAgent.handle",
            new_callable=AsyncMock,
            return_value={
                "current_agent": "billing_agent",
                "response": "We've received your dispute.",
                "messages": [],
            },
        ):
            result = await graph.ainvoke(state)
        assert result["current_agent"] == "billing_agent"

    async def test_state_has_response(self) -> None:
        """After graph execution, state should have a non-empty response."""
        clf = _mock_classifier("balance_check", 0.85)
        graph = build_supervisor(clf)
        state = _make_state("Check my balance", language="en")
        with patch(
            "src.agents.domains.billing.BillingAgent.handle",
            new_callable=AsyncMock,
            return_value={
                "current_agent": "billing_agent",
                "response": "Your balance is N15,000.50.",
                "messages": [],
            },
        ):
            result = await graph.ainvoke(state)
        assert result["response"] != ""

    async def test_response_max_sentences(self) -> None:
        """Agent responses should be max 2 sentences."""
        clf = _mock_classifier("balance_check", 0.85)
        graph = build_supervisor(clf)
        state = _make_state("Check my balance", language="en")
        with patch(
            "src.agents.domains.billing.BillingAgent.handle",
            new_callable=AsyncMock,
            return_value={
                "current_agent": "billing_agent",
                "response": "Your balance is N15,000.50.",
                "messages": [],
            },
        ):
            result = await graph.ainvoke(state)
        # Count sentences by splitting on sentence-ending punctuation
        import re
        sentences = re.split(r'[.!?]+\s', result["response"])
        # Filter empty strings
        sentences = [s for s in sentences if s.strip()]
        assert len(sentences) <= 2

    async def test_messages_appended(self) -> None:
        """Messages should accumulate (via operator.add reducer)."""
        clf = _mock_classifier("greeting", 0.9)
        graph = build_supervisor(clf)
        state = _make_state("Hello", language="en")
        result = await graph.ainvoke(state)
        # Should have original user message + assistant response
        assert len(result["messages"]) >= 2
        roles = [m.role if isinstance(m, AgentMessage) else m["role"] for m in result["messages"]]
        assert "user" in roles
        assert "assistant" in roles
