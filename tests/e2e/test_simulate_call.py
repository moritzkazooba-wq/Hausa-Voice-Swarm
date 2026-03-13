"""E2E tests for the full stack via docker-compose.

Requires: ``docker compose up -d --build --wait`` before running.
Run with: ``uv run pytest tests/e2e/ -v``
"""

from __future__ import annotations

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Health endpoint returns 200 when app is ready."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_simulate_call_returns_response() -> None:
    """Simulate-call endpoint returns a well-formed response."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "Check my balance",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "session_id" in data
        assert "intent" in data
        assert "latency_ms" in data
        assert len(data["response"]) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_simulate_call_with_custom_session_id() -> None:
    """Simulate-call with explicit session ID echoes it back."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/test/simulate-call",
            json={
                "phone_number": "+2348012345678",
                "text": "Help me",
                "session_id": "e2e-test-session",
            },
        )
        data = resp.json()
        assert data["session_id"] == "e2e-test-session"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_metrics_endpoint_has_prometheus_metrics() -> None:
    """Metrics endpoint returns Prometheus exposition format with expected metrics."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "hsv_active_voice_sessions" in body
        assert "hsv_intent_classification_total" in body


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_graphql_balance_query() -> None:
    """GraphQL accountBalance query returns mock customer data."""
    query = '{ accountBalance(phoneNumber: "+2348012345678") { name balance } }'
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/graphql",
            json={"query": query},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["accountBalance"]["name"] == "Amina Bello"
