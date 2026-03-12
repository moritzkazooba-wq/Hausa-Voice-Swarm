"""Tests for configuration settings classes."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from src.config.settings import (
    AppSettings,
    ASRSettings,
    DatabaseSettings,
    KafkaSettings,
    LLMSettings,
    RedisSettings,
    TelephonySettings,
    TTSSettings,
)


class TestAppSettings:
    """AppSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.env == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.mock_llm is True
        assert settings.api_base_url == "http://localhost:8000"

    def test_from_env(self) -> None:
        env = {
            "ENV": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "MOCK_LLM": "false",
            "API_BASE_URL": "https://api.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.env == "production"
        assert settings.debug is True
        assert settings.mock_llm is False
        assert settings.api_base_url == "https://api.example.com"


class TestASRSettings:
    """ASRSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = ASRSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.asr_provider == "intron"
        assert settings.intron_api_key == ""
        assert settings.use_real_asr is False
        assert settings.asr_fallback_enabled is True

    def test_from_env(self) -> None:
        env = {
            "ASR_PROVIDER": "whisper",
            "INTRON_API_KEY": "key-123",
            "USE_REAL_ASR": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = ASRSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.asr_provider == "whisper"
        assert settings.intron_api_key == "key-123"
        assert settings.use_real_asr is True

    def test_invalid_provider(self) -> None:
        env = {"ASR_PROVIDER": "google"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValidationError):
            ASRSettings(_env_file=None)  # type: ignore[call-arg]


class TestTTSSettings:
    """TTSSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = TTSSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.hausa_provider == "intron"
        assert settings.english_provider == "cartesia"
        assert settings.use_real_tts is False


class TestLLMSettings:
    """LLMSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = LLMSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.default_model == "gemini-flash"
        assert settings.complex_model == "gpt-4o"
        assert settings.openai_api_key == ""
        assert settings.google_api_key == ""

    def test_from_env(self) -> None:
        env = {"OPENAI_API_KEY": "sk-test", "GOOGLE_API_KEY": "goog-test"}
        with patch.dict(os.environ, env, clear=True):
            settings = LLMSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.openai_api_key == "sk-test"
        assert settings.google_api_key == "goog-test"


class TestRedisSettings:
    """RedisSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.session_ttl_seconds == 1800

    def test_custom_ttl(self) -> None:
        env = {"SESSION_TTL_SECONDS": "3600"}
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.session_ttl_seconds == 3600


class TestDatabaseSettings:
    """DatabaseSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = DatabaseSettings(_env_file=None)  # type: ignore[call-arg]
        assert "asyncpg" in settings.cockroachdb_url
        assert settings.pool_size == 10


class TestKafkaSettings:
    """KafkaSettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = KafkaSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.topic_prefix == "hsv"


class TestTelephonySettings:
    """TelephonySettings tests."""

    def test_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = TelephonySettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.telephony_provider == "stub"
        assert settings.websocket_port == 8765

    def test_from_env(self) -> None:
        env = {
            "TELEPHONY_PROVIDER": "daily",
            "DAILY_API_KEY": "daily-key",
            "WEBSOCKET_PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = TelephonySettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.telephony_provider == "daily"
        assert settings.daily_api_key == "daily-key"
        assert settings.websocket_port == 9000

    def test_invalid_provider(self) -> None:
        env = {"TELEPHONY_PROVIDER": "twilio"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(ValidationError):
            TelephonySettings(_env_file=None)  # type: ignore[call-arg]
