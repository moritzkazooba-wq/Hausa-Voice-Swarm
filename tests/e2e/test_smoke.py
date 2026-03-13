"""E2E smoke tests against the docker-compose stack.

Requires: docker compose up (app on localhost:8000)
Run with: uv run pytest tests/e2e/ -v
"""

from __future__ import annotations

import httpx
import pytest

BASE_URL = "http://localhost:8000"

pytestmark = pytest.mark.e2e


@pytest.fixture
def client() -> httpx.Client:
    """Synchronous httpx client pointed at the running app."""
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as c:
        yield c  # type: ignore[misc]


class TestBalanceCheck:
    """Scenario A: User asks for their balance."""

    def test_balance_response(self, client: httpx.Client) -> None:
        resp = client.post(
            "/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "I want to check my balance",
            },
        )
        assert resp.status_code == 200
        body = resp.json()

        # Response has required fields
        assert "response" in body
        assert "session_id" in body
        assert "intent" in body
        assert "latency_ms" in body

        # Response mentions balance / naira
        response_lower = body["response"].lower()
        assert "naira" in response_lower or "balance" in response_lower

    def test_metrics_after_call(self, client: httpx.Client) -> None:
        # Make a call first
        client.post(
            "/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "I want to check my balance",
            },
        )
        # Check metrics endpoint shows activity
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "hsv_active_voice_sessions" in resp.text
        assert "hsv_voice_to_voice_latency_ms" in resp.text


class TestPinResetConfirmation:
    """Scenario B: PIN reset requires confirmation flow."""

    def test_pin_reset_needs_confirmation(self, client: httpx.Client) -> None:
        resp = client.post(
            "/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "I need to reset my PIN",
                "session_id": "e2e-pin-reset-001",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "e2e-pin-reset-001"
        assert "response" in body
        assert len(body["response"]) > 0

    def test_pin_reset_confirm(self, client: httpx.Client) -> None:
        # First call — expect confirmation prompt
        resp1 = client.post(
            "/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "I need to reset my PIN",
                "session_id": "e2e-pin-reset-002",
            },
        )
        assert resp1.status_code == 200
        body1 = resp1.json()
        assert "response" in body1

        # Second call with same session — confirm
        resp2 = client.post(
            "/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "yes",
                "session_id": "e2e-pin-reset-002",
            },
        )
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["session_id"] == "e2e-pin-reset-002"
        assert "response" in body2


class TestEscalation:
    """Scenario C: Frustrated user gets escalation ticket."""

    def test_escalation_response(self, client: httpx.Client) -> None:
        resp = client.post(
            "/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "This is ridiculous I've been waiting all day",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert "session_id" in body
        # Agent should provide a response (escalation or general help)
        assert len(body["response"]) > 0


class TestHealthAndMetrics:
    """Infrastructure smoke tests."""

    def test_health_ok(self, client: httpx.Client) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_metrics_prometheus_format(self, client: httpx.Client) -> None:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "hsv_intent_classification_total" in resp.text
