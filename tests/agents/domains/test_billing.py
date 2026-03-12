"""Tests for BillingAgent — uses pytest-httpx to mock GraphQL calls."""

import json
from datetime import UTC, datetime
from typing import Any

from pytest_httpx import HTTPXMock
from src.agents.domains.billing import BillingAgent

# ---------------------------------------------------------------------------
# Realistic GraphQL response fixtures
# ---------------------------------------------------------------------------

BALANCE_RESPONSE: dict[str, Any] = {
    "data": {
        "accountBalance": {
            "id": "11111111-1111-1111-1111-111111111111",
            "phoneNumber": "+2348012345678",
            "name": "Amina Bello",
            "balance": "15000.50",
            "currency": "NGN",
            "plan": "basic",
            "status": "active",
            "region": "kano",
        },
    },
}

TRANSACTION_RESPONSE: dict[str, Any] = {
    "data": {
        "transactionHistory": [
            {
                "id": "aaaa1111-0000-0000-0000-000000000001",
                "accountId": "11111111-1111-1111-1111-111111111111",
                "amount": "500.00",
                "merchant": "MTN Airtime",
                "date": "2026-03-10T14:30:00+00:00",
                "status": "completed",
                "type": "debit",
            },
            {
                "id": "aaaa1111-0000-0000-0000-000000000002",
                "accountId": "11111111-1111-1111-1111-111111111111",
                "amount": "20000.00",
                "merchant": "Salary Credit",
                "date": "2026-03-01T09:00:00+00:00",
                "status": "completed",
                "type": "credit",
            },
        ],
    },
}

PAYMENT_RESPONSE: dict[str, Any] = {
    "data": {
        "processPayment": {
            "success": True,
            "message": "Payment of 500.0 NGN to MTN Airtime requires confirmation.",
            "referenceId": "PAY-2026-00001",
            "requiresConfirmation": True,
        },
    },
}

ESCALATION_RESPONSE: dict[str, Any] = {
    "data": {
        "createEscalationTicket": {
            "success": True,
            "message": "Escalation ticket created for: Wrong charge. Requires confirmation.",
            "referenceId": "ESC-2026-00001",
            "requiresConfirmation": True,
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    intent: str,
    language: str = "en",
    phone: str = "+2348012345678",
    text: str = "test message",
    **context_extra: Any,
) -> dict[str, Any]:
    """Build a minimal agent state dict."""
    return {
        "messages": [
            {
                "role": "user",
                "content": text,
                "timestamp": datetime.now(UTC).isoformat(),
                "agent_name": "user",
            },
        ],
        "language": language,
        "intent": intent,
        "confidence": 0.85,
        "customer_context": {"phone_number": phone, **context_extra},
        "current_agent": "",
        "session_id": "test-session",
        "response": "",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBillingAgentBalanceCheck:
    async def test_balance_check_calls_graphql(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """balance_check should POST to /graphql and return balance info."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=BALANCE_RESPONSE,
        )
        agent = BillingAgent()
        state = _make_state("balance_check")
        result = await agent.handle(state)

        assert result["current_agent"] == "billing_agent"
        assert result["response"] != ""
        # Should mention the balance amount
        assert "15000" in result["response"] or "15,000" in result["response"]

    async def test_balance_check_hausa(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """balance_check in Hausa should respond in Hausa."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=BALANCE_RESPONSE,
        )
        agent = BillingAgent()
        state = _make_state("balance_check", language="ha")
        result = await agent.handle(state)

        assert result["current_agent"] == "billing_agent"
        # Hausa response should contain "Kuɗin" or the balance
        assert "Kuɗin" in result["response"] or "15000" in result["response"]


class TestBillingAgentTransactionHistory:
    async def test_transaction_history_two_calls(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """transaction_history needs balance first (for account ID), then txns."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=BALANCE_RESPONSE,
        )
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=TRANSACTION_RESPONSE,
        )
        agent = BillingAgent()
        state = _make_state("transaction_history")
        result = await agent.handle(state)

        assert result["current_agent"] == "billing_agent"
        assert result["response"] != ""
        # Should have made 2 GraphQL calls
        requests = httpx_mock.get_requests()
        assert len(requests) == 2


class TestBillingAgentPayment:
    async def test_payment_requires_confirmation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """Payment without confirmation should return confirmation request."""
        # No httpx call expected — confirmation check is local
        agent = BillingAgent()
        state = _make_state(
            "payment",
            text="Pay 500 to MTN",
            amount=500.0,
            merchant="MTN Airtime",
            confirmed=False,
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "billing_agent"
        assert "confirm" in result["response"].lower() or "tabbatar" in result["response"].lower()

    async def test_payment_confirmed_calls_mutation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """Payment with confirmed=True should call processPayment mutation."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=PAYMENT_RESPONSE,
        )
        agent = BillingAgent()
        state = _make_state(
            "payment",
            text="Yes, confirm payment",
            amount=500.0,
            merchant="MTN Airtime",
            confirmed=True,
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "billing_agent"
        # Verify the mutation was called
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert "processPayment" in body["query"]

    async def test_payment_confirmation_explicit_yes(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """First call without confirmed should NOT call GraphQL."""
        agent = BillingAgent()
        state = _make_state(
            "payment",
            text="Pay 1000 to DSTV",
            amount=1000.0,
            merchant="DSTV",
            confirmed=False,
        )
        result = await agent.handle(state)

        # No GraphQL calls should have been made
        requests = httpx_mock.get_requests()
        assert len(requests) == 0
        assert result["response"] != ""


class TestBillingAgentDispute:
    async def test_dispute_creates_escalation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """Dispute should create an escalation ticket via GraphQL."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=ESCALATION_RESPONSE,
        )
        agent = BillingAgent()
        state = _make_state(
            "dispute",
            text="I was charged wrong for my airtime",
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "billing_agent"
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert "createEscalationTicket" in body["query"]
        assert "I was charged wrong" in body["variables"]["issue"]

    async def test_dispute_uses_complex_model(self) -> None:
        """Dispute intent should select the complex LLM model (gpt-4o)."""
        agent = BillingAgent()
        model = agent._select_model("dispute")
        assert model == "gpt-4o"

    async def test_simple_intent_uses_default_model(self) -> None:
        """balance_check should use the default model (gemini-flash)."""
        agent = BillingAgent()
        model = agent._select_model("balance_check")
        assert model == "gemini-flash"
