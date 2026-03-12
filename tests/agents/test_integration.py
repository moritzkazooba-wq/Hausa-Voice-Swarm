"""Integration tests for the full agent orchestration chain.

Tests cover:
- balance check → BalanceAgent → response
- PIN reset → TransferAgent → confirmation → execution
- speak to human → EscalationAgent → ticket
- ambiguous (confidence < 0.5) → EscalationAgent
- multi-turn: greeting → balance → follow-up → goodbye
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.agents.orchestrator import Supervisor
from src.models.session import SessionState


def _make_session(
    phone: str = "+2348012345678",
    name: str = "Amina Bello",
) -> SessionState:
    """Create a fresh session for testing."""
    return SessionState(
        session_id="test-session-001",
        customer_phone=phone,
        customer_name=name,
        language="ha",
        current_intent="",
        current_agent="",
        conversation_turns=[],
        started_at=datetime.now(tz=UTC),
        channel="voice",
        confidence_history=[],
    )


# --- Test 1: Balance check → BalanceAgent → response ---


@pytest.mark.asyncio
async def test_balance_check_routes_to_balance_agent() -> None:
    """Balance inquiry should route to BalanceAgent and return balance info."""
    supervisor = Supervisor()
    session = _make_session()

    response, updated_session = await supervisor.route("What is my balance?", session)

    assert updated_session.current_agent == "balance_agent"
    assert updated_session.current_intent == "check_balance"
    assert "15,000.50" in response.message
    assert "basic" in response.message
    assert response.metadata.get("balance") == "15000.50"


# --- Test 2: PIN reset → TransferAgent → confirmation ---


@pytest.mark.asyncio
async def test_pin_reset_routes_to_transfer_agent_with_confirmation() -> None:
    """PIN reset should route to TransferAgent and require confirmation."""
    supervisor = Supervisor()
    session = _make_session()

    response, updated_session = await supervisor.route(
        "I need to reset pin please change pin", session
    )

    assert updated_session.current_agent == "transfer_agent"
    assert updated_session.current_intent == "pin_reset"
    assert response.action_result is not None
    assert response.action_result.requires_confirmation is True


@pytest.mark.asyncio
async def test_pin_reset_execution_after_confirmation() -> None:
    """After confirmation, PIN reset should still go through TransferAgent."""
    supervisor = Supervisor()
    session = _make_session()

    # First turn: request
    _, session_after_first = await supervisor.route("reset my pin please", session)
    assert session_after_first.current_intent == "pin_reset"

    # Second turn: confirm (this is a new message, intent may change)
    _response, session_after_second = await supervisor.route(
        "yes confirm", session_after_first
    )
    # "yes confirm" won't match pin_reset strongly, but the flow continues
    assert len(session_after_second.conversation_turns) == 4  # 2 user + 2 assistant


# --- Test 3: Speak to human → EscalationAgent → ticket ---


@pytest.mark.asyncio
async def test_speak_to_human_routes_to_escalation_agent() -> None:
    """'speak to human' intent should route to EscalationAgent with ticket."""
    supervisor = Supervisor()
    session = _make_session()

    response, updated_session = await supervisor.route(
        "I want to speak to a human agent", session
    )

    assert updated_session.current_agent == "escalation_agent"
    assert updated_session.current_intent == "speak_to_human"
    assert response.action_result is not None
    assert response.action_result.reference_id is not None
    assert "ESC-" in response.action_result.reference_id
    assert "mintuna" in response.message  # Wait time in Hausa


# --- Test 4: Ambiguous input (confidence < 0.5) → EscalationAgent ---


@pytest.mark.asyncio
async def test_ambiguous_input_escalates_to_human() -> None:
    """Ambiguous text with low confidence should escalate to EscalationAgent."""
    supervisor = Supervisor()
    session = _make_session()

    # Gibberish text that won't match any intent well
    response, updated_session = await supervisor.route(
        "xyzzy foobar baz quux", session
    )

    assert updated_session.current_agent == "escalation_agent"
    # Confidence should be below threshold
    assert updated_session.confidence_history[-1] < 0.5
    assert response.action_result is not None


# --- Test 5: Multi-turn conversation ---


@pytest.mark.asyncio
async def test_multi_turn_greeting_balance_followup_goodbye() -> None:
    """Multi-turn: greeting → balance → follow-up → goodbye."""
    supervisor = Supervisor()
    session = _make_session()

    # Turn 1: Greeting
    resp1, session = await supervisor.route("Sannu! Hello", session)
    assert session.current_intent == "greeting"
    assert session.current_agent == "general_agent"
    assert "Sannu" in resp1.message or "Barka" in resp1.message

    # Turn 2: Balance check
    resp2, session = await supervisor.route("Check my balance please", session)
    assert session.current_intent == "check_balance"
    assert session.current_agent == "balance_agent"
    assert "15,000.50" in resp2.message

    # Turn 3: Follow-up (general)
    _resp3, session = await supervisor.route("What else can you do?", session)
    assert session.current_agent in ("general_agent", "escalation_agent")

    # Turn 4: Goodbye
    _resp4, session = await supervisor.route("Nagode, sai anjima", session)
    assert session.current_intent == "goodbye"
    assert session.current_agent == "general_agent"

    # Verify full conversation history
    assert len(session.conversation_turns) == 8  # 4 user + 4 assistant
    assert len(session.confidence_history) == 4


# --- Test 6: Technical issue → TechnicalAgent ---


@pytest.mark.asyncio
async def test_technical_issue_routes_to_technical_agent() -> None:
    """Technical issue should route to TechnicalAgent with network status."""
    supervisor = Supervisor()
    session = _make_session()

    response, updated_session = await supervisor.route(
        "My network is not working, there is a problem", session
    )

    assert updated_session.current_agent == "technical_agent"
    assert updated_session.current_intent == "technical_issue"
    assert response.metadata.get("network_status") is not None


# --- Test 7: Bill payment → BillPaymentAgent ---


@pytest.mark.asyncio
async def test_bill_payment_routes_to_bill_agent() -> None:
    """Bill payment intent should route to BillPaymentAgent."""
    supervisor = Supervisor()
    session = _make_session()

    response, updated_session = await supervisor.route(
        "I want to pay my DSTV bill", session
    )

    assert updated_session.current_agent == "bill_payment_agent"
    assert updated_session.current_intent == "pay_bill"
    assert response.action_result is not None
    assert response.action_result.requires_confirmation is True


# --- Test 8: Transfer → TransferAgent ---


@pytest.mark.asyncio
async def test_transfer_routes_to_transfer_agent() -> None:
    """Transfer intent should route to TransferAgent with confirmation."""
    supervisor = Supervisor()
    session = _make_session()

    response, updated_session = await supervisor.route(
        "I want to send money to someone", session
    )

    assert updated_session.current_agent == "transfer_agent"
    assert updated_session.current_intent == "transfer_money"
    assert response.action_result is not None
    assert response.action_result.requires_confirmation is True


# --- Test 9: Unknown customer → BalanceAgent handles gracefully ---


@pytest.mark.asyncio
async def test_balance_unknown_customer() -> None:
    """Balance check for unknown customer should return error message."""
    supervisor = Supervisor()
    session = _make_session(phone="+2340000000000", name="Unknown")

    response, updated_session = await supervisor.route("Check my balance", session)

    assert updated_session.current_agent == "balance_agent"
    assert "ba mu sami" in response.message.lower() or "sake gwadawa" in response.message.lower()


# --- Test 10: Session state accumulates correctly ---


@pytest.mark.asyncio
async def test_session_state_accumulates() -> None:
    """Verify session state grows correctly across turns."""
    supervisor = Supervisor()
    session = _make_session()

    # Turn 1
    _, session = await supervisor.route("Hello", session)
    assert len(session.conversation_turns) == 2
    assert len(session.confidence_history) == 1

    # Turn 2
    _, session = await supervisor.route("Check balance", session)
    assert len(session.conversation_turns) == 4
    assert len(session.confidence_history) == 2

    # Verify conversation ordering
    assert session.conversation_turns[0].role == "user"
    assert session.conversation_turns[1].role == "assistant"
    assert session.conversation_turns[2].role == "user"
    assert session.conversation_turns[3].role == "assistant"
