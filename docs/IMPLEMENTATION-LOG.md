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

---

## Phase 2: GraphQL API with DataLoader

### Key Files Created/Modified
- `src/api/schema.py` — Strawberry types, Query, Mutation classes, schema object
- `src/api/dataloader.py` — `AccountLoader`, `TransactionLoader` (batched N+1 prevention)
- `src/api/mock_resolvers.py` — deterministic mock data + async resolver functions
- `src/api/app.py` — FastAPI app factory with all endpoints
- `src/api/__init__.py` — re-exports `create_app`, `schema`
- `tests/api/test_graphql.py` — 12 tests (queries, mutations, DataLoader batching)
- `tests/api/test_endpoints.py` — 4 tests (/health, /metrics, /test/simulate-call)

### Public Interfaces

**Strawberry Types:** `AccountType`, `TransactionType`, `ActionResultType`, `NetworkStatusType`

**GraphQL Queries:**
- `accountBalance(phoneNumber: String!) -> AccountType` — uses AccountLoader
- `transactionHistory(accountId: ID!, last: Int = 10) -> [TransactionType!]!` — uses TransactionLoader
- `networkStatus(region: String!) -> NetworkStatusType`

**GraphQL Mutations (all return `ActionResultType` with `requiresConfirmation=true`):**
- `processPayment(phoneNumber: String!, amount: Float!, merchant: String!)`
- `resetPin(phoneNumber: String!)`
- `changePlan(phoneNumber: String!, newPlan: String!)`
- `createEscalationTicket(phoneNumber: String!, issue: String!)`

**FastAPI Endpoints:**
- `GET /graphql` — Strawberry GraphQL playground + POST for queries
- `GET /health` — `{"status": "ok"}` when ready, 503 during startup
- `GET /metrics` — placeholder (wired in Phase 6)
- `POST /test/simulate-call` — stub returning `{"response": "Pipeline not yet connected", "session_id": "stub"}`

**DataLoaders:**
- `create_account_loader() -> DataLoader[str, CustomerProfile | None]`
- `create_transaction_loader() -> DataLoader[UUID, list[Transaction]]`

**Context:** `GraphQLContext(BaseContext)` — provides `account_loader`, `transaction_loader` per request

**App Factory:** `create_app() -> FastAPI`

### Integration Points
- App entry: `from src.api import create_app; app = create_app()`
- Schema access: `from src.api import schema`
- Mock resolvers: `from src.api.mock_resolvers import get_customer, get_transactions, ...`
- Resolvers import models from `src.models` (CustomerProfile, Transaction, ActionResult, NetworkStatus)
- Context getter creates fresh DataLoaders per request to avoid cross-request caching

### Known Limitations
- All resolvers use mock data (`src/api/mock_resolvers.py`) — replace with real DB in Phase 3
- `/metrics` returns empty string — wired to Prometheus in Phase 6
- `/test/simulate-call` is a stub — wired to voice pipeline in Phase 7a
- No authentication middleware yet (future phase)
- `_ready` flag is module-level — for multi-worker production, replace with DB connectivity check

---

## Phase 5: Kafka Event Bus

### Key Files Created/Modified
- `src/events/schemas.py` — `BaseEvent`, `IntentClassifiedEvent`, `ToolExecutedEvent`, `SessionStartedEvent`, `SessionEndedEvent`, `EscalationTriggeredEvent`
- `src/events/producer.py` — `KafkaEventProducer` (async aiokafka), topic constants, event→topic routing
- `src/events/consumer.py` — `BaseKafkaConsumer` (abstract), `AnalyticsConsumer` (Project C placeholder)
- `src/events/session_events.py` — helper functions for emitting events from agents
- `src/events/__init__.py` — re-exports all public symbols
- `tests/events/test_schemas.py` — 13 tests (field validation, JSON roundtrips)
- `tests/events/test_producer.py` — 8 tests (topic routing, serialization, start/stop lifecycle)
- `tests/events/test_session_events.py` — 7 tests (helper functions with mock producer)

### Public Interfaces

**Event Schemas (all extend `BaseEvent` with `session_id`, `timestamp`):**
- `IntentClassifiedEvent(utterance, intent, confidence, language, model_used)`
- `ToolExecutedEvent(agent_name, tool_name, success, duration_ms, result_summary, metadata?)`
- `SessionStartedEvent(customer_phone, channel, language)`
- `SessionEndedEvent(reason, duration_seconds, total_turns)`
- `EscalationTriggeredEvent(from_agent, reason, customer_phone, priority?)`

**Producer:**
- `KafkaEventProducer(settings?)` — `start()`, `stop()`, `publish(event)`
- Topics: `hsv.intents`, `hsv.tools`, `hsv.sessions`, `hsv.escalations`

**Consumer:**
- `BaseKafkaConsumer(*topics, group_id, settings?)` — `start()`, `stop()`, `run()`, abstract `handle_message()`
- `AnalyticsConsumer(settings?)` — subscribes to all 4 topics, group `hsv-analytics`

**Session Event Helpers:**
- `emit_intent_classified(producer, *, session_id, utterance, intent, confidence, language, model_used)`
- `emit_tool_executed(producer, *, session_id, agent_name, tool_name, success, duration_ms, result_summary, metadata?)`
- `emit_session_started(producer, *, session_id, customer_phone, channel, language)`
- `emit_session_ended(producer, *, session_id, reason, duration_seconds, total_turns)`
- `emit_escalation(producer, *, session_id, from_agent, reason, customer_phone, priority?)`

### Integration Points
- All events: `from src.events import IntentClassifiedEvent, KafkaEventProducer, ...`
- Helpers: `from src.events import emit_intent_classified, emit_tool_executed, ...`
- Agent instrumentation: call `emit_intent_classified` after intent classification, `emit_tool_executed` after domain agent actions
- Session lifecycle: call `emit_session_started`/`emit_session_ended` from voice pipeline or session manager
- Producer lifecycle: `start()` in FastAPI lifespan, `stop()` on shutdown
- Config: uses `KafkaSettings` from `src.config` (`kafka_bootstrap_servers`, `topic_prefix`)

### Known Limitations
- `AnalyticsConsumer.handle_message` is a placeholder — forwards to structlog only (Project C will implement)
- Producer does not retry on transient Kafka errors (add tenacity in production hardening phase)
- No schema registry integration — events are plain JSON (sufficient for current scale)
- Agent instrumentation hooks exist as helpers but are not yet wired into agent stubs (agents are still stubs)
