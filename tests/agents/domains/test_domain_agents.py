"""Tests for domain agent mock responses and LLM integration."""

from __future__ import annotations

import pytest
from src.agents.domains.balance import BalanceAgent
from src.agents.domains.bills import BillsAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.transfer import TransferAgent


@pytest.mark.asyncio
async def test_balance_agent_mock_response() -> None:
    agent = BalanceAgent()
    result = await agent.run("sess-1", "What is my balance?")
    assert result.success is True
    assert "15,000" in result.message


@pytest.mark.asyncio
async def test_transfer_agent_requires_confirmation() -> None:
    agent = TransferAgent()
    result = await agent.run("sess-2", "Send 5000 to Ahmed")
    assert result.success is True
    assert result.requires_confirmation is True


@pytest.mark.asyncio
async def test_bills_agent_requires_confirmation() -> None:
    agent = BillsAgent()
    result = await agent.run("sess-3", "Pay my electricity bill")
    assert result.success is True
    assert result.requires_confirmation is True


@pytest.mark.asyncio
async def test_general_agent_response() -> None:
    agent = GeneralAgent()
    result = await agent.run("sess-4", "Help me")
    assert result.success is True
    assert result.message != ""


@pytest.mark.asyncio
async def test_agent_names_are_correct() -> None:
    assert BalanceAgent().agent_name == "balance"
    assert TransferAgent().agent_name == "transfer"
    assert BillsAgent().agent_name == "bills"
    assert GeneralAgent().agent_name == "general"


@pytest.mark.asyncio
async def test_complexity_routing() -> None:
    """Simple agents use default_model, complex agents use complex_model."""
    assert BalanceAgent().complexity == "simple"
    assert GeneralAgent().complexity == "simple"
    assert TransferAgent().complexity == "complex"
    assert BillsAgent().complexity == "complex"
