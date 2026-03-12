"""Tests for AccountAgent — uses pytest-httpx to mock GraphQL calls."""

import json
from datetime import UTC, datetime
from typing import Any

from pytest_httpx import HTTPXMock
from src.agents.domains.account import AccountAgent

# ---------------------------------------------------------------------------
# Realistic GraphQL response fixtures
# ---------------------------------------------------------------------------

ACCOUNT_RESPONSE: dict[str, Any] = {
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

PIN_RESET_RESPONSE: dict[str, Any] = {
    "data": {
        "resetPin": {
            "success": True,
            "message": "PIN reset requires confirmation. A new PIN will be sent via SMS.",
            "referenceId": "PIN-2026-00001",
            "requiresConfirmation": True,
        },
    },
}

PLAN_CHANGE_RESPONSE: dict[str, Any] = {
    "data": {
        "changePlan": {
            "success": True,
            "message": "Plan change to premium requires confirmation.",
            "referenceId": "PLAN-2026-00001",
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


class TestAccountInfo:
    async def test_account_info_calls_graphql(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """account_info should query account details via GraphQL."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=ACCOUNT_RESPONSE,
        )
        agent = AccountAgent()
        state = _make_state("account_info")
        result = await agent.handle(state)

        assert result["current_agent"] == "account_agent"
        assert result["response"] != ""
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert "accountBalance" in body["query"]


class TestPinReset:
    async def test_pin_reset_requires_confirmation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """PIN reset without confirmation should return confirmation request."""
        agent = AccountAgent()
        state = _make_state(
            "pin_reset",
            text="I forgot my PIN",
            confirmed=False,
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "account_agent"
        # No GraphQL calls for unconfirmed request
        requests = httpx_mock.get_requests()
        assert len(requests) == 0
        # Response should mention confirmation or PIN
        assert "confirm" in result["response"].lower() or "pin" in result["response"].lower()

    async def test_pin_reset_confirmed_calls_mutation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """PIN reset with confirmed=True should call resetPin mutation."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=PIN_RESET_RESPONSE,
        )
        agent = AccountAgent()
        state = _make_state(
            "pin_reset",
            text="Yes, reset my PIN",
            confirmed=True,
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "account_agent"
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert "resetPin" in body["query"]

    async def test_pin_reset_generates_verification_code(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """Confirmed PIN reset should generate a 6-digit verification code."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=PIN_RESET_RESPONSE,
        )
        agent = AccountAgent()
        state = _make_state(
            "pin_reset",
            text="Yes, reset my PIN",
            confirmed=True,
        )
        # Access the _dispatch_tool directly to check verification code
        tool_result = await agent._dispatch_tool("pin_reset", state)
        assert "_verification_code" in tool_result
        code = tool_result["_verification_code"]
        assert len(code) == 6
        assert code.isdigit()


class TestPlanChange:
    async def test_plan_change_requires_confirmation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """Plan change without confirmation should return confirmation request."""
        agent = AccountAgent()
        state = _make_state(
            "plan_change",
            text="Change my plan to premium",
            new_plan="premium",
            confirmed=False,
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "account_agent"
        requests = httpx_mock.get_requests()
        assert len(requests) == 0
        assert "confirm" in result["response"].lower() or "tabbatar" in result["response"].lower()

    async def test_plan_change_confirmed_calls_mutation(
        self, httpx_mock: HTTPXMock,
    ) -> None:
        """Plan change with confirmed=True should call changePlan mutation."""
        httpx_mock.add_response(
            url="http://localhost:8000/graphql",
            json=PLAN_CHANGE_RESPONSE,
        )
        agent = AccountAgent()
        state = _make_state(
            "plan_change",
            text="Yes, change my plan",
            new_plan="premium",
            confirmed=True,
        )
        result = await agent.handle(state)

        assert result["current_agent"] == "account_agent"
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert "changePlan" in body["query"]
        assert body["variables"]["newPlan"] == "premium"


class TestAccountAgentModelSelection:
    async def test_all_intents_use_gemini_flash(self) -> None:
        """All AccountAgent intents should use gemini-flash."""
        agent = AccountAgent()
        assert agent.default_llm == "gemini-flash"
