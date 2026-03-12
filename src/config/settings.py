"""Application settings via pydantic-settings (reads from env / .env)."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    mock_llm: bool = True
    api_base_url: str = "http://localhost:8000"


class ASRSettings(BaseSettings):
    """Automatic speech recognition settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    asr_provider: Literal["intron", "whisper"] = "intron"
    intron_api_key: str = ""
    whisper_model_path: str = ""
    asr_fallback_enabled: bool = True
    use_real_asr: bool = False


class TTSSettings(BaseSettings):
    """Text-to-speech settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    hausa_provider: str = "intron"
    english_provider: str = "cartesia"
    filler_audio_dir: str = "assets/fillers"
    use_real_tts: bool = False


class LLMSettings(BaseSettings):
    """LLM provider settings (via LiteLLM)."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    default_model: str = "gemini-flash"
    complex_model: str = "gpt-4o"
    litellm_api_base: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""


class RedisSettings(BaseSettings):
    """Redis connection and session settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379"
    session_ttl_seconds: int = 1800


class DatabaseSettings(BaseSettings):
    """CockroachDB connection settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    cockroachdb_url: str = "postgresql+asyncpg://root@localhost:26257/defaultdb"
    pool_size: int = 10


class KafkaSettings(BaseSettings):
    """Kafka / Redpanda settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    kafka_bootstrap_servers: str = "localhost:9092"
    topic_prefix: str = "hsv"


class TelephonySettings(BaseSettings):
    """Voice transport / telephony settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    telephony_provider: Literal["daily", "telnyx", "stub"] = "stub"
    daily_api_key: str = ""
    telnyx_sip_uri: str = ""
    telnyx_api_key: str = ""
    websocket_port: int = 8765
