"""Tests for supervisor routing edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from src.agents.supervisor import route_to_agent


@pytest.mark.asyncio
async def test_route_to_agent_fallback_to_general() -> None:
    """Unknown intent in _AGENT_MAP should fall back to general agent."""
    mock_classification = AsyncMock()
    mock_classification.intent = "nonexistent_intent"
    mock_classification.confidence = 0.3

    with patch(
        "src.agents.supervisor.classify_intent",
        return_value=mock_classification,
    ):
        result, classification = await route_to_agent("sess-fallback", "some unknown phrase")

    assert result.success is True
    assert classification.intent == "nonexistent_intent"
