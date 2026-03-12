"""Tests for REST endpoints: /health, /metrics, /test/simulate-call."""

from __future__ import annotations

import pytest
import src.api.app as app_module
from httpx import ASGITransport, AsyncClient
from src.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    # ASGITransport doesn't run lifespan, so set _ready manually.
    app_module._ready = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app_module._ready = False


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_metrics_returns_prometheus_exposition(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    # Should contain Prometheus exposition format with our custom metrics
    assert "hsv_active_voice_sessions" in resp.text
    assert "hsv_intent_classification_total" in resp.text
    assert "text/plain" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_simulate_call_returns_pipeline_response(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/test/simulate-call",
        json={"phone_number": "+2348012345678", "text": "Ina so in biya kuɗi"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Pipeline is wired — response comes from agent supervisor
    assert "response" in body
    assert isinstance(body["response"], str)
    assert len(body["response"]) > 0
    assert "session_id" in body
    assert "intent" in body
    assert "latency_ms" in body
    assert isinstance(body["latency_ms"], (int, float))


@pytest.mark.asyncio
async def test_simulate_call_with_session_id(client: AsyncClient) -> None:
    resp = await client.post(
        "/test/simulate-call",
        json={
            "phone_number": "+2348012345678",
            "text": "Check balance",
            "session_id": "test-session-123",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "test-session-123"
    assert "response" in body
    assert "intent" in body
