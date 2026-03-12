# Hausa Voice Swarm

Voice agent system for mobile money customer support in Hausa (with English code-switching). Pipecat for voice orchestration, LangGraph for multi-agent routing, deployed on GKE.

Part of a 3-project portfolio. This project consumes the fine-tuned Whisper-Hausa model from Project A and feeds Kafka events + Redis session state into Project C.

## Tech Stack
- Python 3.12+, mypy strict, ruff, async throughout
- Pipecat: voice pipeline orchestration
- LangGraph: multi-agent orchestration (orchestrator-worker pattern)
- Strawberry + FastAPI: GraphQL API layer
- Redis: session cache (TTL 30 min)
- CockroachDB: multi-region customer data (REGIONAL BY ROW)
- Kafka: inter-service events
- Prometheus: custom metrics (active_sessions, v2v_latency_ms)
- GKE: custom-metric HPA. Terraform: all IaC
- Pydantic v2: all data models
- LiteLLM: LLM abstraction (GPT-4o complex, Gemini Flash simple)

## Project Structure
See @docs/IMPLEMENTATION-LOG.md for what has been built and key interfaces.

## Commands
- `uv run ruff check src/ tests/` — lint
- `uv run mypy src/` — type check
- `uv run pytest tests/ -v --ignore=tests/e2e` — unit/integration tests (no docker needed)
- `uv run pytest tests/e2e/ -v` — e2e tests (requires docker compose up)
- `docker compose up` — local dev

## Package Management (uv — NEVER use pip directly)
- `uv add <package>` — add a dependency
- `uv add --dev <package>` — add a dev dependency
- `uv remove <package>` — remove a dependency
- `uv sync` — install from lockfile (fast, reproducible)
- `uv run <command>` — run any command in the project environment
- `uv lock` — regenerate uv.lock after manual pyproject.toml edits
- Commit uv.lock to git — it pins every transitive dependency

## Cross-Cutting Rules (apply to ALL layers)
- Type hints on all functions, mypy strict
- Pydantic models for all data structures, never raw dicts
- Async everywhere — no blocking calls on event loop
- Use structlog for structured logging
- Financial mutations: always return requires_confirmation=True on first call
- Agent responses: max 2 sentences for low-literacy users
- All services export Prometheus metrics at /metrics
- Commit messages: conventional commits (feat:, fix:, docs:)

## API Keys for Development
- LLM calls use mock responses by default (MOCK_LLM=true in .env)
- Set MOCK_LLM=false and provide OPENAI_API_KEY / GOOGLE_API_KEY for real LLM calls
- ASR/TTS use stub processors that simulate realistic latencies
- Set USE_REAL_ASR=true with INTRON_API_KEY for real Intron API calls
