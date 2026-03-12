"""Tests for cost-based LLM model selection."""

import os
from unittest.mock import patch

from src.agents.llm_router import COMPLEX_INTENTS, SIMPLE_INTENTS, select_model


class TestSelectModel:
    def test_simple_intent_uses_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            model = select_model("balance_check")
        assert model == "gemini-flash"

    def test_complex_intent_uses_complex(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            model = select_model("dispute")
        assert model == "gpt-4o"

    def test_technical_issue_is_complex(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            model = select_model("technical_issue")
        assert model == "gpt-4o"

    def test_greeting_uses_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            model = select_model("greeting")
        assert model == "gemini-flash"

    def test_unknown_intent_uses_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            model = select_model("other")
        assert model == "gemini-flash"

    def test_reads_from_settings(self) -> None:
        env = {"DEFAULT_MODEL": "custom-fast", "COMPLEX_MODEL": "custom-smart"}
        with patch.dict(os.environ, env, clear=True):
            assert select_model("greeting") == "custom-fast"
            assert select_model("dispute") == "custom-smart"

    def test_simple_and_complex_disjoint(self) -> None:
        """SIMPLE_INTENTS and COMPLEX_INTENTS should not overlap."""
        assert SIMPLE_INTENTS.isdisjoint(COMPLEX_INTENTS)
