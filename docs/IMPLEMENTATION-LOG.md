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

---

## Phase 6: Prometheus Metrics

### Key Files Created/Modified
- `src/metrics/definitions.py` — all Prometheus metric objects (Gauges, Counters, Histograms)
- `src/metrics/middleware.py` — `MetricsMiddleware` for FastAPI HTTP request metrics
- `src/metrics/__init__.py` — re-exports all metrics and middleware
- `src/agents/intent.py` — intent classifier with `classify_intent()`, instruments `intent_classification_total`
- `src/agents/domains/base.py` — `BaseDomainAgent` ABC with `run()` instrumenting `tool_execution_total`
- `src/agents/domains/balance.py` — `BalanceAgent(BaseDomainAgent)`
- `src/agents/domains/transfer.py` — `TransferAgent(BaseDomainAgent)` (requires_confirmation)
- `src/agents/domains/bills.py` — `BillsAgent(BaseDomainAgent)` (requires_confirmation)
- `src/agents/domains/general.py` — `GeneralAgent(BaseDomainAgent)`
- `src/agents/domains/__init__.py` — re-exports all agent classes
- `src/agents/supervisor.py` — `route_to_agent()` supervisor, instruments `agent_routing_total`
- `src/agents/__init__.py` — re-exports `classify_intent`, `route_to_agent`
- `src/api/app.py` — wired `/metrics` endpoint via `generate_latest()`, added `MetricsMiddleware`
- `tests/api/test_endpoints.py` — updated metrics test to verify Prometheus exposition format
- `tests/metrics/test_definitions.py` — 8 tests (registry, gauge, counters, histograms, labels)
- `tests/metrics/test_instrumentation.py` — 6 tests (intent classifier, domain agents, supervisor metrics)

### Public Interfaces

**Metric Definitions (`src.metrics.definitions`):**
- `active_voice_sessions` — Gauge
- `voice_to_voice_latency_ms` — Histogram
- `asr_latency_ms` — Histogram (labels: `model`, `intent`)
- `tts_latency_ms` — Histogram (labels: `model`, `intent`)
- `llm_latency_ms` — Histogram (labels: `model`, `intent`)
- `intent_classification_total` — Counter (labels: `intent`, `classifier_type`)
- `tool_execution_total` — Counter (labels: `tool_name`, `success`)
- `agent_routing_total` — Counter (labels: `target_agent`)
- `session_duration_seconds` — Histogram
- `cost_per_interaction_usd` — Histogram
- `http_requests_total` — Counter (labels: `method`, `path`, `status_code`)
- `http_request_duration_ms` — Histogram (labels: `method`, `path`)

**Middleware:**
- `MetricsMiddleware(BaseHTTPMiddleware)` — auto-records `http_requests_total` and `http_request_duration_ms`

**Intent Classifier (`src.agents.intent`):**
- `classify_intent(utterance: str, *, classifier_type: str = "sentence-transformers") -> ClassificationResult`
- `ClassificationResult(intent, confidence, utterance, classifier_type, elapsed_ms)`

**Domain Agents (`src.agents.domains`):**
- `BaseDomainAgent` — ABC with `run(session_id, utterance) -> ActionResult` (instrumented) and abstract `_execute()`
- `BalanceAgent`, `TransferAgent`, `BillsAgent`, `GeneralAgent` — concrete implementations

**Supervisor (`src.agents.supervisor`):**
- `route_to_agent(session_id: str, utterance: str) -> tuple[ActionResult, ClassificationResult]`

### Integration Points
- Metrics import: `from src.metrics import active_voice_sessions, intent_classification_total, ...`
- Middleware: added automatically in `create_app()` — no manual wiring needed
- `/metrics` endpoint: returns `prometheus_client.generate_latest()` in Prometheus exposition format
- Agent usage: `from src.agents import classify_intent, route_to_agent`
- Domain agents: `from src.agents.domains import BalanceAgent, TransferAgent, ...`
- Voice pipeline should call `active_voice_sessions.inc()` / `.dec()` on session start/end
- Voice pipeline should observe `voice_to_voice_latency_ms`, `asr_latency_ms`, `tts_latency_ms`
- LLM calls should observe `llm_latency_ms.labels(model=..., intent=...).observe(ms)`
- Session lifecycle should observe `session_duration_seconds` and `cost_per_interaction_usd`

### Known Limitations
- Intent classifier returns mock results (always "general" at 0.85 confidence) — real sentence-transformers model in future phase
- Domain agents return mock responses — real DB/API integration in future phase
- `cost_per_interaction_usd` not yet computed automatically — must be observed manually
- No per-worker metric aggregation — single-process `prometheus_client` registry (sufficient for dev)

---

## Phase 7a: Pipecat Pipeline Skeleton

### Key Files Created/Modified
- `src/voice/vad_config.py` — Silero VAD configuration with `VADProcessor` wrapper (300ms pad, 0.5 threshold, 0.8s endpointing)
- `src/voice/asr.py` — `StubASRProcessor(FrameProcessor)` simulates transcription from audio frames, instruments `asr_latency_ms`
- `src/voice/tts.py` — `StubTTSProcessor(FrameProcessor)` simulates speech synthesis, forwards TextFrame + silent audio, instruments `tts_latency_ms`
- `src/voice/agent_bridge.py` — `AgentBridgeProcessor(FrameProcessor)` connects pipecat to LangGraph supervisor via `route_to_agent()`
- `src/voice/transport.py` — `StubTransport` (text-in/text-out for testing), `StubInputTransport`, `StubOutputTransport`, `create_transport()` factory
- `src/voice/fillers.py` — `FillerProcessor` logs when response latency exceeds 500ms threshold
- `src/voice/pipeline.py` — `create_voice_pipeline()` wires transport → VAD → ASR → filler → agent bridge → TTS → output
- `src/voice/ws_server.py` — WebSocket server stub using `websockets.asyncio.server`, started/stopped via FastAPI lifespan
- `src/voice/vad.py` — Re-exports from `vad_config` for backwards compatibility
- `src/voice/__init__.py` — Updated re-exports for all new public symbols
- `src/api/app.py` — Wired `/test/simulate-call` to `route_to_agent()`, lifespan starts/stops WebSocket server
- `tests/voice/test_vad_config.py` — 3 tests (VADProcessor creation, params validation)
- `tests/voice/test_transport.py` — 7 tests (input passthrough, output capture, factory, event signaling)
- `tests/voice/test_agent_bridge.py` — 3 tests (TranscriptionFrame→TextFrame, passthrough, route_to_agent call)
- `tests/voice/test_pipeline.py` — 2 tests (pipeline construction, processor count = 9 including internal Source/Sink)
- `tests/voice/test_fillers.py` — 2 tests (filler triggers above/below 500ms threshold)
- `tests/api/test_endpoints.py` — Updated simulate-call tests for real response fields

### Public Interfaces

**Pipeline Construction:**
- `create_voice_pipeline(transport, session_id) -> tuple[Pipeline, PipelineTask, AgentBridgeProcessor]`
- Pipeline order: transport.input() → VADProcessor → StubASRProcessor → FillerProcessor → AgentBridgeProcessor → StubTTSProcessor → transport.output()

**Transport:**
- `StubTransport(input_text: str)` — `.input()`, `.output()`, `.response_ready`, `.collected_text`, `.inject_text(task)`
- `create_transport(settings?, *, input_text="") -> StubTransport` — factory with "stub", "daily" (NotImplementedError), "telnyx" (NotImplementedError)

**Agent Bridge:**
- `AgentBridgeProcessor(session_id: str)` — processes TranscriptionFrame → calls `route_to_agent()` → pushes TextFrame
- `.last_classification` property for accessing classification result

**VAD Configuration:**
- `create_vad_params() -> VADParams` — confidence=0.5, start_secs=0.3, stop_secs=0.8, min_volume=0.6
- `create_vad_processor() -> VADProcessor` — wraps SileroVADAnalyzer as FrameProcessor

**Fillers:**
- `FillerProcessor()` — logs when latency between TranscriptionFrame and TextFrame exceeds 500ms

**WebSocket Server:**
- `start_ws_server(port=8765) -> asyncio.Server` — stub server for future telephony

### Integration Points
- Voice pipeline: `from src.voice import create_voice_pipeline, StubTransport, create_transport`
- Agent bridge: `from src.voice import AgentBridgeProcessor`
- VAD: `from src.voice import create_vad_params, create_vad_processor`
- Pipeline uses `route_to_agent()` from `src.agents.supervisor` inside AgentBridgeProcessor
- `/test/simulate-call` calls `route_to_agent()` directly (pipecat's streaming audio lifecycle is incompatible with synchronous text simulation)
- Lifespan starts WebSocket server on `TelephonySettings.websocket_port` (default 8765)
- Instruments: `active_voice_sessions` (gauge), `voice_to_voice_latency_ms` (histogram), `asr_latency_ms`, `tts_latency_ms`

### Known Limitations
- ASR/TTS are stubs — real Intron/Cartesia integration activated via `USE_REAL_ASR=true` / `USE_REAL_TTS=true` (future phase)
- VAD is structurally included but won't process real audio in stub mode
- FillerProcessor logs only — no actual filler audio playback yet
- WebSocket server logs connections but doesn't process audio
- `/test/simulate-call` bypasses pipecat pipeline, calls `route_to_agent()` directly
- Daily and Telnyx transports raise `NotImplementedError` — placeholders for future telephony integration

---

## Phase 8a: Test Fixture Refactor

### Key Files Created/Modified
- `tests/conftest.py` — Layer 1 (base) + Layer 2 (service) fixtures: `fakeredis_client`, `db_session`, `mock_kafka_producer`, `mock_graphql_client`
- `tests/api/conftest.py` — **(new)** consolidated `app` and `client` fixtures (removed from test_endpoints.py and test_graphql.py)
- `tests/events/conftest.py` — **(new)** `mock_producer` with mocked internal transport for producer routing tests
- `tests/agents/conftest.py` — **(new)** Layer 3 agent fixtures: `intent_classifier`, `supervisor`, domain agents
- `tests/voice/conftest.py` — **(new)** Layer 4 voice fixtures: `bridge`, `filler`, `stub_transport`
- `tests/api/test_endpoints.py` — removed local `app`/`client` fixtures, uses api conftest
- `tests/api/test_graphql.py` — removed local `app`/`client` fixtures, uses api conftest
- `tests/events/test_producer.py` — removed local `mock_producer`, uses events conftest
- `tests/events/test_session_events.py` — switched from local `mock_producer` to root `mock_kafka_producer`
- `tests/voice/test_agent_bridge.py` — removed local `bridge` fixture, uses voice conftest
- `tests/voice/test_fillers.py` — removed local `filler` fixture, uses voice conftest

### Public Interfaces

**Layer 1 — Base fixtures (root conftest):**
- `fakeredis_client` — `AsyncGenerator[aioredis.Redis, None]`, async fakeredis connection
- `db_session` — skips test when `COCKROACHDB_URL` not set (placeholder for async SQLAlchemy session)

**Layer 2 — Service fixtures (root conftest):**
- `mock_kafka_producer` — `KafkaEventProducer` with `publish` as `AsyncMock`, records published events
- `mock_graphql_client` — `AsyncGenerator[AsyncClient, None]`, httpx client wired to FastAPI app

**Layer 3 — Agent fixtures (`tests/agents/conftest.py`):**
- `balance_agent`, `transfer_agent`, `bills_agent`, `general_agent` — domain agent instances
- `intent_classifier` — returns `classify_intent` function
- `supervisor` — returns `route_to_agent` function

**Layer 4 — Voice fixtures (`tests/voice/conftest.py`):**
- `stub_transport` — `StubTransport("test input")`
- `bridge` — `AgentBridgeProcessor(session_id="test-session-001")`
- `filler` — `FillerProcessor()`

**API fixtures (`tests/api/conftest.py`):**
- `app` — `FastAPI` from `create_app()`
- `client` — `AsyncClient` with `ASGITransport`, `_ready=True` for lifespan bypass

**Events fixtures (`tests/events/conftest.py`):**
- `mock_producer` — `KafkaEventProducer` with mocked `_producer.send_and_wait` for transport-level tests

### Integration Points
- Root fixtures available to all tests: `fakeredis_client`, `db_session`, `mock_kafka_producer`, `mock_graphql_client`
- Subdirectory fixtures scoped to their test directories — no cross-directory imports
- No circular imports between fixture modules
- 128 tests pass, mypy clean, ruff clean

### Known Limitations
- `db_session` is a skip-only placeholder — yields no session until SQLAlchemy ORM models exist (Phase 2+)
- `mock_graphql_client` uses mock resolvers — will need update when real DB resolvers are wired
- Layer 3 agent fixtures return mock-only agents — update when real LLM/DB integration lands
- `voice_pipeline` fixture not yet implemented (requires async pipeline lifecycle management)
