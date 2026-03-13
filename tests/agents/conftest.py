"""Agent test fixtures (Layer 3) — intent classifier, supervisor, domain agents."""

from __future__ import annotations

import pytest
from src.agents.domains.balance import BalanceAgent
from src.agents.domains.bills import BillsAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.transfer import TransferAgent
from src.agents.intent import classify_intent
from src.agents.supervisor import route_to_agent


@pytest.fixture
def balance_agent() -> BalanceAgent:
    """BalanceAgent configured with mock tools."""
    return BalanceAgent()


@pytest.fixture
def transfer_agent() -> TransferAgent:
    """TransferAgent configured with mock tools (requires_confirmation)."""
    return TransferAgent()


@pytest.fixture
def bills_agent() -> BillsAgent:
    """BillsAgent configured with mock tools (requires_confirmation)."""
    return BillsAgent()


@pytest.fixture
def general_agent() -> GeneralAgent:
    """GeneralAgent configured with mock tools."""
    return GeneralAgent()


@pytest.fixture
def intent_classifier():
    """Pre-loaded intent classifier function (MOCK_LLM=true by default)."""
    return classify_intent


@pytest.fixture
def supervisor():
    """Supervisor route function configured with MOCK_LLM=true."""
    return route_to_agent
