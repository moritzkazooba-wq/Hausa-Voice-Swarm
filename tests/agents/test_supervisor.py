"""Tests for supervisor routing via LangGraph orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from src.agents.intent import ClassificationResult
from src.agents.supervisor import route_to_agent


@pytest.mark.asyncio
async def test_route_to_agent_fallback_to_general() -> None:
    """Unknown intent in the graph should fall back to general agent."""
    mock_result = ClassificationResult(
        intent="general",
        confidence=0.5,
        utterance="some unknown phrase",
        classifier_type="keyword",
        elapsed_ms=0.1,
    )

    with patch(
        "src.agents.orchestrator.classify_intent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result, classification = await route_to_agent("sess-fallback", "some unknown phrase")

    assert result.success is True
    assert classification.intent == "general"


@pytest.mark.asyncio
async def test_route_to_agent_routes_balance() -> None:
    """Balance utterance should route to balance agent."""
    result, classification = await route_to_agent("sess-bal", "What is my balance?")
    assert classification.intent == "balance"
    assert result.success is True
    assert "balance" in result.message.lower() or "15,000" in result.message


@pytest.mark.asyncio
async def test_route_to_agent_routes_transfer() -> None:
    """Transfer utterance should route to transfer agent."""
    result, classification = await route_to_agent("sess-xfer", "I want to transfer money")
    assert classification.intent == "transfer"
    assert result.requires_confirmation is True


@pytest.mark.asyncio
async def test_route_to_agent_routes_bills() -> None:
    """Bill payment utterance should route to bills agent."""
    result, classification = await route_to_agent("sess-bill", "Pay my DSTV bill")
    assert classification.intent == "bills"
    assert result.requires_confirmation is True
