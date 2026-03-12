# Implementation Log

Tracks what has been built, key file paths, and interface contracts.

---

## Phase 0: Project Scaffold

### Key Files Created
- `pyproject.toml` — project config, dependencies, mypy strict, ruff rules, pytest markers
- `uv.lock` — pinned transitive dependencies (committed for reproducibility)
- `.gitignore` — Python, cache, env, ML model caches
- `Dockerfile` — multi-stage uv build (build → slim runtime)
- `docker-compose.yml` — app + redis + cockroachdb + redpanda + prometheus
- `prometheus.yml` — scrape config for app:8000/metrics
- `.github/workflows/ci.yml` — lint, typecheck, unit tests via uv
- `.env.example` — all env vars with safe defaults

### Source Tree (`src/`)
- `src/voice/` — pipeline.py, asr.py, tts.py, vad.py (stubs)
- `src/agents/` — orchestrator.py, intent.py, base.py (stubs)
- `src/agents/domains/` — balance.py, transfer.py, bills.py, general.py (stubs)
- `src/api/` — app.py, schema.py, dataloader.py (stubs)
- `src/models/` — session.py, customer.py, transaction.py (stubs)
- `src/db/` — engine.py, repositories.py, session_store.py (stubs)
- `src/events/` — producer.py, consumer.py, schemas.py (stubs)
- `src/metrics/` — collectors.py (stub)
- `src/config/` — settings.py (stub)
- `src/utils/` — logging.py (stub)
- `src/py.typed` — PEP 561 marker

### Test Tree (`tests/`)
- `tests/conftest.py` — fakeredis fixture, cockroachdb skip fixture
- Subdirectories mirror src: models, config, api, db, agents, events, metrics, voice, e2e

### Child CLAUDE.md Files
- `src/agents/CLAUDE.md` — orchestrator-worker, LangGraph, intent classifier, LiteLLM routing
- `src/voice/CLAUDE.md` — Pipecat pipeline, ASR/TTS/VAD, telephony config
- `src/api/CLAUDE.md` — Strawberry GraphQL, health, metrics, simulate-call
- `src/db/CLAUDE.md` — CockroachDB REGIONAL BY ROW, Redis session store, repository pattern
- `infrastructure/CLAUDE.md` — Terraform modules, GKE, custom HPA
- `k8s/CLAUDE.md` — manifests, HPA, PDB, NetworkPolicy

### Integration Points
- No active integrations yet — all modules are stubs
- `tests/conftest.py` exports `mock_redis` and `cockroachdb_url` fixtures

### Known Limitations
- Sentence-transformers model not pre-cached (requires HuggingFace Hub access)
- No Alembic migrations initialized yet (Phase 1)
- No actual test cases yet (Phase 1+)

---

## Phase 1: Pydantic Models and Config

### Key Files Created/Modified
- `src/models/customer.py` — `CustomerProfile`, `NetworkStatus`
- `src/models/transaction.py` — `Transaction`, `ActionResult`
- `src/models/session.py` — `AgentMessage`, `SessionState`
- `src/models/voice.py` — `VoiceMetrics`
- `src/models/__init__.py` — re-exports all models
- `src/config/settings.py` — 8 settings classes (AppSettings, ASRSettings, TTSSettings, LLMSettings, RedisSettings, DatabaseSettings, KafkaSettings, TelephonySettings)
- `src/config/__init__.py` — re-exports all settings
- `tests/models/test_customer.py` — 13 tests (phone regex, decimal, serialization)
- `tests/models/test_transaction.py` — 11 tests (validation, roundtrip, optional fields)
- `tests/models/test_session.py` — 11 tests (literals, nested models, channels)
- `tests/models/test_voice.py` — 2 tests (validation, roundtrip)
- `tests/config/test_settings.py` — 15 tests (defaults, env loading, invalid providers)

### Public Interfaces
- `src.models.CustomerProfile(id, phone_number, name, balance, currency, plan, status, region)`
- `src.models.Transaction(id, account_id, amount, merchant, date, status, type)`
- `src.models.ActionResult(success, message, reference_id?, requires_confirmation?)`
- `src.models.SessionState(session_id, customer_phone, customer_name, language, current_intent, current_agent, conversation_turns, started_at, channel, confidence_history)`
- `src.models.AgentMessage(role, content, timestamp, agent_name, metadata?)`
- `src.models.VoiceMetrics(session_id, v2v_latency_ms, asr_latency_ms, tts_latency_ms, llm_latency_ms, intent, model_used)`
- `src.models.NetworkStatus(region, status, latency_ms, last_checked)`
- `src.config.AppSettings`, `ASRSettings`, `TTSSettings`, `LLMSettings`, `RedisSettings`, `DatabaseSettings`, `KafkaSettings`, `TelephonySettings`

### Integration Points
- All models: `from src.models import CustomerProfile, SessionState, ...`
- All config: `from src.config import AppSettings, RedisSettings, ...`
- Config classes read from env vars / `.env` file via pydantic-settings
- `CustomerProfile.phone_number` validates Nigerian format: `+234XXXXXXXXXX`
- `ActionResult.requires_confirmation` — financial agents must set True on first call

### Known Limitations
- No database ORM models yet — Pydantic models only (SQLAlchemy models in Phase 2)
- Config classes don't yet validate inter-field dependencies (e.g. real ASR requires API key)
