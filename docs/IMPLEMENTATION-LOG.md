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

## Phase 4c: Technical Agent, Escalation Agent, Integration Tests

### Key Files Created/Modified
- `src/agents/base.py` — `BaseAgent` ABC, `AgentResponse` dataclass
- `src/agents/intent.py` — `classify_intent()` keyword matcher, `IntentResult` dataclass
- `src/agents/orchestrator.py` — `Supervisor` (orchestrator-worker routing, confidence gating)
- `src/agents/__init__.py` — re-exports `BaseAgent`, `AgentResponse`, `Supervisor`, `classify_intent`, `IntentResult`
- `src/agents/domains/balance.py` — `BalanceAgent` (gemini-flash, balance lookup via mock_resolvers)
- `src/agents/domains/transfer.py` — `TransferAgent` (gpt-4o, requires_confirmation)
- `src/agents/domains/bills.py` — `BillPaymentAgent` (gpt-4o, requires_confirmation)
- `src/agents/domains/general.py` — `GeneralAgent` (gemini-flash, greeting/goodbye/FAQ)
- `src/agents/domains/technical.py` — `TechnicalAgent` (gpt-4o, networkStatus query, step-by-step guidance)
- `src/agents/domains/escalation.py` — `EscalationAgent` (gpt-4o, createEscalationTicket mutation, mock wait time)
- `src/agents/domains/__init__.py` — re-exports all 6 domain agents
- `tests/agents/test_integration.py` — 11 integration tests (full orchestration chain)

### Public Interfaces

**Base:**
- `BaseAgent` — ABC with `async handle(user_message, session, history) -> AgentResponse`
- `AgentResponse(message, action_result?, route_to?, metadata?)`

**Intent Classification:**
- `classify_intent(text: str) -> IntentResult` — keyword-based, Hausa + English code-switching
- `IntentResult(intent, confidence, top_intents)` — 9 intents: check_balance, transfer_money, pay_bill, pin_reset, technical_issue, speak_to_human, greeting, goodbye, general

**Supervisor (Orchestrator):**
- `Supervisor.route(user_message, session) -> tuple[AgentResponse, SessionState]`
- Routes by intent; escalates when confidence < 0.5
- `CONFIDENCE_THRESHOLD = 0.5`
- `INTENT_AGENT_MAP` — maps intent strings to agent classes

**Domain Agents (all implement `BaseAgent.handle`):**
- `BalanceAgent` — queries `get_customer()`, returns balance + plan
- `TransferAgent` — calls `process_payment()`, returns `requires_confirmation=True`
- `BillPaymentAgent` — calls `process_payment()`, returns `requires_confirmation=True`
- `GeneralAgent` — greeting/goodbye responses, general help
- `TechnicalAgent` — calls `get_network_status()`, returns diagnostics (healthy/degraded/down)
- `EscalationAgent` — calls `create_escalation_ticket()`, returns ticket ref + estimated wait time

### Integration Points
- Orchestrator entry: `from src.agents import Supervisor; s = Supervisor(); resp, session = await s.route(msg, session)`
- Agents consume `src.api.mock_resolvers` for data (replace with real DB repositories later)
- Agents consume `src.models.SessionState` for conversation state
- `EscalationAgent` triggered by: `speak_to_human` intent, confidence < 0.5, or emotional distress detection (future)
- `TechnicalAgent` queries `get_network_status(region)` from mock_resolvers

### Known Limitations
- Intent classifier uses keyword matching — swap to sentence-transformers cosine similarity for production
- `TechnicalAgent` defaults to `"kano"` region (SessionState lacks `region` field — add in future phase)
- No LiteLLM integration yet — agents return static/mock responses; `MOCK_LLM=true` assumed
- `EscalationAgent` uses hardcoded wait times per region — wire to real queue metrics later
- No emotional distress detection — escalation only via explicit intent or low confidence
