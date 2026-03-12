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

## Phase 3: Database Layer with Seed Data

### Key Files Created/Modified
- `src/db/engine.py` — async engine singleton + session factory
- `src/db/models.py` — `AccountModel`, `TransactionModel`, `PlanModel` (SQLAlchemy ORM)
- `src/db/repositories.py` — `AccountRepository`, `TransactionRepository`
- `src/db/session_store.py` — `SessionStore` (Redis, TTL 30 min)
- `src/db/seed.py` — seed script (10K accounts, 100K txns, 5 plans)
- `src/db/__init__.py` — re-exports all DB components
- `alembic.ini` + `src/db/migrations/` — Alembic async migration setup
- `src/db/migrations/versions/001_initial_schema.py` — accounts, transactions, plans tables
- `src/api/resolvers.py` — resolver dispatch (mock vs. real DB)
- `src/api/dataloader.py` — DataLoaders accept optional `session_factory`
- `src/api/schema.py` — mutations route through `resolvers` module
- `src/api/app.py` — lifespan initializes DB engine when `mock_resolvers=false`
- `src/config/settings.py` — added `mock_resolvers: bool = True` to `AppSettings`
- `tests/db/test_session_store.py` — 8 tests (fakeredis)
- `tests/db/test_repositories.py` — 9 tests (`@pytest.mark.db`, skipped without DB)

### Public Interfaces

**Engine:**
- `async init_engine(url: str, pool_size: int = 10) -> None`
- `async dispose_engine() -> None`
- `get_engine() -> AsyncEngine`
- `get_session_factory() -> async_sessionmaker[AsyncSession]`

**ORM Models:** `AccountModel`, `TransactionModel`, `PlanModel` — each has `to_pydantic()` method

**Repositories:**
- `AccountRepository(session)`: `get_by_phone`, `get_by_id`, `get_batch_by_phones`, `update_balance`, `update_plan`
- `TransactionRepository(session)`: `get_by_account(limit)`, `get_batch_by_accounts`, `create_transaction`

**Session Store:**
- `SessionStore(redis, ttl_seconds)`: `get_session`, `save_session`, `extend_ttl`, `delete_session`

**Resolver Dispatch (src/api/resolvers.py):**
- `get_customers_batch_db(session_factory, phones)`, `get_transactions_batch_db(session_factory, ids)`
- `get_network_status`, `process_payment`, `reset_pin`, `change_plan`, `create_escalation_ticket`

**Seed:** `python -m src.db.seed [--check-empty]`

### Integration Points
- `from src.db import init_engine, get_session_factory, AccountRepository, ...`
- `AppSettings.mock_resolvers` controls mock vs. real DB (default: True)
- DataLoaders: `create_account_loader(session_factory=None)` — None = mock mode
- GraphQLContext: `GraphQLContext(session_factory=None)` — passed from app lifespan
- Alembic: `COCKROACHDB_URL=... uv run alembic upgrade head`

### Known Limitations
- Mutations still return mock `ActionResult` (real mutation logic deferred to agent layer)
- `NetworkStatus` has no DB table — stays mock
- Seed script uses `random` (not crypto-safe) — fine for test data
- No Alembic `downgrade` tested in CI yet
- DB repository tests require running CockroachDB (`COCKROACHDB_URL` env var)

---

## Phase 4a: Intent Classifier and LangGraph Supervisor Skeleton

### Key Files Created/Modified
- `src/agents/intent.py` — IntentClassifier with embedding fast path + keyword/LLM fallback
- `src/agents/orchestrator.py` — LangGraph StateGraph supervisor with conditional routing
- `src/agents/base.py` — BaseAgent ABC for domain agents
- `src/agents/llm_router.py` — Cost-based model selection (gemini-flash vs gpt-4o)
- `src/agents/prompts.py` — System prompt templates (Hausa, English, Pidgin)
- `src/agents/domains/balance.py` — Balance inquiry agent (stub)
- `src/agents/domains/transfer.py` — Transfer/PIN reset agent (stub)
- `src/agents/domains/bills.py` — Bills/plan change agent (stub)
- `src/agents/domains/general.py` — General/dispute agent (stub)
- `src/agents/__init__.py` — Re-exports all public interfaces
- `src/agents/domains/__init__.py` — Re-exports domain agents
- `.claude/skills/langgraph-*` — LangGraph skills from langchain-ai/langchain-skills
- `tests/agents/test_intent.py` — 18 tests (classifier, keyword, model mocking)
- `tests/agents/test_orchestrator.py` — 16 tests (routing, graph execution)
- `tests/agents/test_llm_router.py` — 7 tests (cost routing)
- `tests/agents/test_prompts.py` — 7 tests (prompt templates)

### Public Interfaces
- `IntentClassifier()` — lazy-loads `paraphrase-multilingual-MiniLM-L12-v2`, `.classify(text) -> IntentResult`
- `IntentResult(intent, confidence, classifier_type, latency_ms)` — Pydantic model
- `INTENTS: list[str]` — 11 supported intents
- `INTENT_EXAMPLES: dict[str, list[str]]` — 5+ Hausa, 5+ English, 2+ Pidgin per intent
- `SupervisorState(TypedDict)` — messages, language, intent, confidence, customer_context, current_agent, session_id, response
- `build_supervisor(classifier) -> CompiledStateGraph` — builds and compiles the LangGraph
- `route_intent(state) -> "greeting" | "escalation" | "domain"` — routing function
- `BaseAgent` ABC — `.handle(state) -> dict[str, Any]`
- `BalanceAgent`, `TransferAgent`, `BillsAgent`, `GeneralAgent` — domain stubs
- `select_model(intent) -> str` — returns LLM model name based on intent complexity
- `build_system_prompt(language, customer_name) -> str` — parameterized prompt

### Integration Points
- Intent classifier: `from src.agents import IntentClassifier`; call `await classifier.classify(text)`
- Supervisor: `from src.agents import build_supervisor`; `graph = build_supervisor(classifier)`; `result = await graph.ainvoke(state)`
- Cost router: `from src.agents import select_model`; `model = select_model(intent)`
- Prompts: `from src.agents import build_system_prompt`; `prompt = build_system_prompt("ha", "Amina")`
- Domain agents: `from src.agents.domains import BalanceAgent, ...`

### Known Limitations
- Domain agents are stubs returning hardcoded responses (real implementation in Phase 4b)
- Sentence-transformers model not pre-cached — first call downloads ~420MB
- Hausa accuracy not validated against real model (mocked in tests)
- LiteLLM slow path untested with real API keys (mocked)
- No persistence/checkpointing on the LangGraph yet (Phase 5)

---

## Phase 4b: Billing and Account Domain Agents

### Key Files Created/Modified
- `src/agents/domains/base.py` — `DomainAgent` base class with `_call_tool` (httpx GraphQL), `_generate_response` (mock/LLM), `_dispatch_tool` (abstract)
- `src/agents/domains/billing.py` — `BillingAgent` for balance_check, transaction_history, payment, dispute
- `src/agents/domains/account.py` — `AccountAgent` for pin_reset, plan_change, account_info
- `src/agents/domains/__init__.py` — updated exports (added `AccountAgent`, `BillingAgent`, `DomainAgent`)
- `src/agents/__init__.py` — updated exports
- `src/agents/orchestrator.py` — rewired `INTENT_AGENT_MAP` and `DOMAIN_AGENTS` to use new agents
- `tests/agents/domains/test_billing.py` — 9 tests (balance, transactions, payment confirmation, dispute escalation)
- `tests/agents/domains/test_account.py` — 7 tests (account info, PIN reset flow, plan change flow)
- `tests/agents/test_orchestrator.py` — updated assertions for new agent names, added httpx mock patches

### Public Interfaces

**DomainAgent (base class):**
- `name: str`, `description: str`, `handled_intents: ClassVar[list[str]]`, `available_tools: ClassVar[list[str]]`, `default_llm: str`
- `async handle(state) -> dict[str, Any]` — full process: dispatch tool → generate response
- `async _call_tool(operation, variables) -> dict` — POST GraphQL to `AppSettings.api_base_url + "/graphql"` via httpx
- `async _generate_response(intent, language, tool_result, phone_number, state) -> str` — mock (canned) or LiteLLM
- `async _dispatch_tool(intent, state) -> dict` — abstract, subclasses implement routing

**BillingAgent:**
- `handled_intents`: balance_check, transaction_history, payment, dispute
- `_select_model(intent)`: gpt-4o for disputes, gemini-flash for all others
- Payment: requires `customer_context.confirmed=True` before calling `processPayment` mutation
- Dispute: creates escalation ticket via `createEscalationTicket` mutation

**AccountAgent:**
- `handled_intents`: pin_reset, plan_change, account_info
- `default_llm`: gemini-flash for all intents
- PIN reset: requires confirmation → generates 6-digit mock verification code
- Plan change: requires confirmation → calls `changePlan` mutation

### Integration Points
- Supervisor: `INTENT_AGENT_MAP` routes to `"billing"`, `"account"`, or `"general"` keys
- `DOMAIN_AGENTS`: `{"billing": BillingAgent(), "account": AccountAgent(), "general": GeneralAgent()}`
- GraphQL tool calls use `AppSettings.api_base_url` (configurable, NOT hardcoded localhost)
- Tests use `pytest-httpx` `HTTPXMock` fixture — no real server needed
- Import: `from src.agents.domains import BillingAgent, AccountAgent, DomainAgent`

### Known Limitations
- `_generate_response` in mock mode uses canned templates — no dynamic LLM generation
- `GeneralAgent` remains a stub (handles technical_issue, other)
- Payment/PIN/plan confirmation is stateless — no session-level tracking of confirmation state
- `_call_tool` creates a new `httpx.AsyncClient` per call (no connection pooling yet)
- No retry/circuit-breaker on GraphQL calls yet
