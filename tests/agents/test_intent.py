"""Tests for intent classifier (mock and real modes)."""

from __future__ import annotations

import pytest
from src.agents.intent import classify_intent


@pytest.mark.asyncio
async def test_classify_intent_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """With MOCK_LLM=true (default), always returns 'general'."""
    monkeypatch.setenv("MOCK_LLM", "true")
    result = await classify_intent("Check my balance")
    assert result.intent == "general"
    assert result.confidence == 0.85


@pytest.mark.asyncio
async def test_classify_intent_real_fallback_on_model_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When model can't be loaded, gracefully falls back to general."""
    monkeypatch.setenv("MOCK_LLM", "false")
    # Force model to fail by patching _get_model
    import src.agents.intent as intent_mod

    original = intent_mod._model
    intent_mod._model = None  # reset singleton

    def _fail_model() -> None:
        msg = "model not available"
        raise RuntimeError(msg)

    monkeypatch.setattr(intent_mod, "_get_model", _fail_model)
    try:
        result = await classify_intent("Check my balance")
        assert result.intent == "general"
        assert result.confidence == 0.5
    finally:
        intent_mod._model = original


def _model_available() -> bool:
    """Check if sentence-transformers model can be loaded."""
    try:
        from src.agents.intent import _get_model

        _get_model()
    except Exception:
        return False
    return True


_skip_no_model = pytest.mark.skipif(
    not _model_available(),
    reason="sentence-transformers model not available (no network or cache)",
)


@_skip_no_model
@pytest.mark.asyncio
async def test_classify_intent_real_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """With real classifier, 'Check my balance' → 'balance'."""
    monkeypatch.setenv("MOCK_LLM", "false")
    result = await classify_intent("Check my balance")
    assert result.intent == "balance"
    assert result.confidence > 0.5


@_skip_no_model
@pytest.mark.asyncio
async def test_classify_intent_real_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    """With real classifier, Hausa transfer request → 'transfer'."""
    monkeypatch.setenv("MOCK_LLM", "false")
    result = await classify_intent("Ina so in aika kudi")
    assert result.intent == "transfer"
    assert result.confidence > 0.5


@_skip_no_model
@pytest.mark.asyncio
async def test_classify_intent_real_bills(monkeypatch: pytest.MonkeyPatch) -> None:
    """With real classifier, 'Pay my bills' → 'bills'."""
    monkeypatch.setenv("MOCK_LLM", "false")
    result = await classify_intent("Pay my bills")
    assert result.intent == "bills"
    assert result.confidence > 0.5


@_skip_no_model
@pytest.mark.asyncio
async def test_classify_intent_real_general(monkeypatch: pytest.MonkeyPatch) -> None:
    """With real classifier, 'Help me' → 'general'."""
    monkeypatch.setenv("MOCK_LLM", "false")
    result = await classify_intent("Help me")
    assert result.intent == "general"
    assert result.confidence > 0.3
