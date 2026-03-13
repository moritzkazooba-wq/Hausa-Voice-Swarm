"""Tests for the LangGraph StateGraph orchestrator."""

from __future__ import annotations

import pytest
from src.agents.orchestrator import orchestrator_graph, run_orchestrator


@pytest.mark.asyncio
async def test_orchestrator_routes_balance() -> None:
    state = await run_orchestrator("test-orch-1", "What is my account balance?")
    assert state["intent"] == "balance"
    assert state["success"] is True
    assert state["response"] != ""


@pytest.mark.asyncio
async def test_orchestrator_routes_transfer() -> None:
    state = await run_orchestrator("test-orch-2", "Transfer money to Ahmed")
    assert state["intent"] == "transfer"
    assert state["requires_confirmation"] is True


@pytest.mark.asyncio
async def test_orchestrator_routes_bills() -> None:
    state = await run_orchestrator("test-orch-3", "Pay my DSTV bill")
    assert state["intent"] == "bills"
    assert state["requires_confirmation"] is True


@pytest.mark.asyncio
async def test_orchestrator_routes_general() -> None:
    state = await run_orchestrator("test-orch-4", "Hello good morning")
    assert state["intent"] == "general"
    assert state["success"] is True


@pytest.mark.asyncio
async def test_orchestrator_preserves_session_id() -> None:
    state = await run_orchestrator("my-session-id", "Check balance")
    assert state["session_id"] == "my-session-id"


def test_graph_is_compiled() -> None:
    """The orchestrator graph should be pre-compiled at import time."""
    assert orchestrator_graph is not None
