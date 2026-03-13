"""Tests for the keyword-based intent classifier."""

from __future__ import annotations

import pytest
from src.agents.intent import classify_intent


@pytest.mark.asyncio
async def test_balance_english() -> None:
    result = await classify_intent("What is my balance?")
    assert result.intent == "balance"
    assert result.confidence >= 0.75


@pytest.mark.asyncio
async def test_balance_hausa() -> None:
    result = await classify_intent("Nawa ne kudi na?")
    assert result.intent == "balance"


@pytest.mark.asyncio
async def test_transfer_english() -> None:
    result = await classify_intent("I want to transfer money to my friend")
    assert result.intent == "transfer"


@pytest.mark.asyncio
async def test_transfer_hausa() -> None:
    result = await classify_intent("Ina so in tura aikawa")
    assert result.intent == "transfer"


@pytest.mark.asyncio
async def test_bills_english() -> None:
    result = await classify_intent("Pay my electricity bill")
    assert result.intent == "bills"


@pytest.mark.asyncio
async def test_bills_brand_name() -> None:
    result = await classify_intent("I want to recharge my MTN airtime")
    assert result.intent == "bills"


@pytest.mark.asyncio
async def test_bills_dstv() -> None:
    result = await classify_intent("Pay DSTV subscription")
    assert result.intent == "bills"


@pytest.mark.asyncio
async def test_general_fallback() -> None:
    result = await classify_intent("Hello, how are you?")
    assert result.intent == "general"
    assert result.confidence == 0.50


@pytest.mark.asyncio
async def test_classifier_type_is_keyword() -> None:
    result = await classify_intent("Check balance")
    assert result.classifier_type == "keyword"


@pytest.mark.asyncio
async def test_high_confidence_multiple_keywords() -> None:
    result = await classify_intent("Check my account balance remaining")
    assert result.intent == "balance"
    assert result.confidence >= 0.85


@pytest.mark.asyncio
async def test_result_contains_utterance() -> None:
    utterance = "Send money to my mother"
    result = await classify_intent(utterance)
    assert result.utterance == utterance
