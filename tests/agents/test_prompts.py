"""Tests for system prompt templates."""

from src.agents.prompts import LANGUAGE_NAMES, build_system_prompt


class TestBuildSystemPrompt:
    def test_hausa_prompt(self) -> None:
        prompt = build_system_prompt("ha", "Amina Bello")
        assert "Hausa" in prompt

    def test_english_prompt(self) -> None:
        prompt = build_system_prompt("en", "John Doe")
        assert "English" in prompt

    def test_pidgin_prompt(self) -> None:
        prompt = build_system_prompt("pcm", "Emeka")
        assert "Nigerian Pidgin" in prompt

    def test_customer_name_included(self) -> None:
        prompt = build_system_prompt("en", "Amina Bello")
        assert "Amina Bello" in prompt

    def test_max_sentences_instruction(self) -> None:
        prompt = build_system_prompt("en", "Test")
        assert "Maximum 2 sentences" in prompt

    def test_unknown_language_defaults_english(self) -> None:
        prompt = build_system_prompt("xx", "Test")
        assert "English" in prompt

    def test_all_languages_covered(self) -> None:
        """All supported languages should be in LANGUAGE_NAMES."""
        for lang in ("ha", "en", "pcm"):
            assert lang in LANGUAGE_NAMES
