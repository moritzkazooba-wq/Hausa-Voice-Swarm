"""Tests that metrics are recorded after agent operations."""

from __future__ import annotations

import pytest
from src.agents.domains.balance import BalanceAgent
from src.agents.domains.bills import BillsAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.transfer import TransferAgent
from src.agents.intent import classify_intent
from src.agents.supervisor import route_to_agent
from src.metrics.definitions import (
    agent_routing_total,
    intent_classification_total,
    tool_execution_total,
)


@pytest.mark.asyncio
async def test_classify_intent_increments_counter() -> None:
    """classify_intent should increment intent_classification_total."""
    result = await classify_intent("Ina so in duba balance na")
    # Keyword classifier recognises "balance" in the utterance
    assert result.intent == "balance"
    assert result.classifier_type == "keyword"

    val = intent_classification_total.labels(
        intent="balance", classifier_type="keyword"
    )._value.get()
    assert val >= 1


@pytest.mark.asyncio
async def test_domain_agent_increments_tool_counter() -> None:
    """Running a domain agent should increment tool_execution_total."""
    agent = BalanceAgent()
    before = tool_execution_total.labels(
        tool_name="balance", success="True"
    )._value.get()

    result = await agent.run("test-session", "Check my balance")
    assert result.success is True

    after = tool_execution_total.labels(
        tool_name="balance", success="True"
    )._value.get()
    assert after == before + 1


@pytest.mark.asyncio
async def test_transfer_agent_requires_confirmation() -> None:
    """Transfer agent should require confirmation and record metric."""
    agent = TransferAgent()
    result = await agent.run("test-session", "Send money")
    assert result.requires_confirmation is True

    val = tool_execution_total.labels(
        tool_name="transfer", success="True"
    )._value.get()
    assert val >= 1


@pytest.mark.asyncio
async def test_bills_agent_requires_confirmation() -> None:
    """Bills agent should require confirmation and record metric."""
    agent = BillsAgent()
    result = await agent.run("test-session", "Pay my bill")
    assert result.requires_confirmation is True

    val = tool_execution_total.labels(
        tool_name="bills", success="True"
    )._value.get()
    assert val >= 1


@pytest.mark.asyncio
async def test_general_agent_records_metric() -> None:
    """General agent should record tool execution metric."""
    agent = GeneralAgent()
    result = await agent.run("test-session", "Help me")
    assert result.success is True

    val = tool_execution_total.labels(
        tool_name="general", success="True"
    )._value.get()
    assert val >= 1


@pytest.mark.asyncio
async def test_supervisor_route_records_metrics() -> None:
    """route_to_agent should record both classification and routing metrics."""
    routing_before = agent_routing_total.labels(target_agent="general")._value.get()

    result, classification = await route_to_agent("test-session", "What can you do?")
    assert result.success is True
    assert classification.intent == "general"

    routing_after = agent_routing_total.labels(target_agent="general")._value.get()
    assert routing_after == routing_before + 1
