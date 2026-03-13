# Technical Decisions — Hausa Voice Swarm

Architecture Decision Records (ADRs) for key technology and design choices.

---

## ADR-001: Pipecat for Voice Orchestration

**Status:** Accepted

**Context:** We need a real-time voice pipeline that handles VAD → ASR → agent → TTS with sub-800ms latency on 3G+ networks. Options considered: custom WebSocket pipeline, LiveKit Agents, Pipecat.

**Decision:** Use Pipecat as the voice pipeline framework.

**Rationale:**
- Frame-based processor model maps directly to our pipeline stages (VAD, ASR, filler, bridge, TTS)
- Built-in support for Silero VAD, multiple ASR/TTS providers, and transport layers (Daily, WebSocket)
- Async-native Python — integrates cleanly with our FastAPI + LangGraph stack
- Processor composition allows inserting custom components (FillerProcessor, AgentBridgeProcessor) without forking
- Active development with production deployments at scale

**Consequences:**
- Tied to Pipecat's frame/processor abstractions for voice components
- Transport layer currently stub-only — Daily and Telnyx transports need implementation for production telephony
- Pipeline lifecycle management adds complexity vs. simple request/response

---

## ADR-002: LangGraph for Multi-Agent Orchestration

**Status:** Accepted

**Context:** Customer support requires routing between specialized domain agents (balance, transfer, bills, general) based on intent classification. Need orchestration that supports the supervisor-worker pattern with state management.

**Decision:** Use LangGraph with an orchestrator-worker pattern.

**Rationale:**
- Native supervisor pattern: orchestrator classifies intent, routes to specialized worker agents
- State graph model aligns with conversation state transitions
- Built-in support for conditional routing, parallel execution, and human-in-the-loop
- Integrates with LiteLLM for multi-model routing (Flash vs GPT-4o)
- Checkpointing enables conversation recovery after failures

**Consequences:**
- Additional abstraction layer over direct LLM calls — adds ~5ms overhead per routing decision
- Learning curve for graph-based agent composition
- State serialization must be kept lean for Redis session store compatibility

---

## ADR-003: Cost-Based LLM Routing (70% Flash / 30% GPT-4o)

**Status:** Accepted

**Context:** At 10M+ interactions/month with ~3 LLM calls each, LLM cost is a significant line item. Need to balance response quality with cost efficiency.

**Decision:** Route 70% of LLM calls to Gemini 2.0 Flash and 30% to GPT-4o via LiteLLM, based on query complexity.

**Rationale:**
- Flash is ~33× cheaper per input token and ~33× cheaper per output token than GPT-4o
- Simple queries (balance checks, confirmations, greetings) don't need GPT-4o reasoning capacity
- LiteLLM abstraction allows changing routing ratios without code changes — just config
- Intent classifier confidence score drives routing: high confidence → Flash, low confidence → GPT-4o
- At 10M interactions: 70/30 split saves ~$18K/month vs all-GPT-4o

**Consequences:**
- Flash responses may be lower quality for nuanced Hausa/English code-switching
- Routing logic adds a decision point that must be monitored (track quality per model)
- Need A/B testing framework to validate that Flash quality is acceptable for simple intents

---

## ADR-004: CockroachDB with REGIONAL BY ROW

**Status:** Accepted

**Context:** Mobile money customer data must be stored with low-latency access across Nigerian regions. Need multi-region consistency without manual sharding.

**Decision:** Use CockroachDB Serverless with `REGIONAL BY ROW` partitioning.

**Rationale:**
- `REGIONAL BY ROW` automatically pins each row to the region specified in its `region` column
- Reads from the local region are fast (~5ms); cross-region reads are consistent but slower
- Serverless pricing ($1/1M RUs) aligns with our scale — no idle capacity cost
- Strong consistency (serializable isolation) is critical for financial transactions
- Automatic rebalancing handles growth without manual intervention

**Consequences:**
- CockroachDB-specific SQL extensions (`REGIONAL BY ROW`) reduce portability
- Cross-region transactions (e.g., transfer between regions) incur higher latency (~50-100ms)
- Serverless tier has throughput limits — may need dedicated cluster at very high scale

---

## ADR-005: Custom HPA on Active Voice Sessions

**Status:** Accepted

**Context:** Standard CPU/memory-based HPA doesn't reflect actual voice pipeline load. A pod at 30% CPU might be handling 10 concurrent voice sessions at full capacity due to GPU/memory constraints.

**Decision:** Use HPA v2 with a custom `hsv_active_voice_sessions` Prometheus metric via prometheus-adapter.

**Rationale:**
- Voice sessions are the actual bottleneck — each session holds GPU memory, audio buffers, and WebSocket connections
- Target of 5 sessions per pod based on g2-standard-4 capacity (4 vCPU, 16GB, 1 GPU)
- prometheus-adapter maps Prometheus gauge → Kubernetes custom metrics API with no custom controller needed
- Aggressive scale-up (+5 pods/30s) handles traffic spikes; conservative scale-down (300s stabilization) prevents session drops
- Range 2–50 pods covers baseline through 4,500 concurrent sessions

**Consequences:**
- Requires prometheus-adapter deployment and APIService registration
- Metric must be accurate — stale `active_voice_sessions` gauge causes incorrect scaling
- Need to ensure session cleanup on pod termination (300s graceful shutdown)

---

## ADR-006: Redis for Session State (TTL 30 min)

**Status:** Accepted

**Context:** Voice sessions need fast read/write state access for conversation context, intent history, and customer profile caching. State must survive individual request boundaries but not persist permanently.

**Decision:** Use Redis (GCP Memorystore) as the session state store with 30-minute TTL.

**Rationale:**
- Sub-millisecond reads for conversation state during real-time voice processing
- TTL-based expiry naturally handles session cleanup — no garbage collection needed
- 2GB instance handles ~100K concurrent sessions with ~20KB state each
- Memorystore provides HA with automatic failover
- fakeredis enables fast, isolated unit testing without infrastructure

**Consequences:**
- Session state is ephemeral — lost on Redis failure (acceptable for voice sessions; CockroachDB has durable data)
- 30-min TTL means dropped calls that reconnect after 30 min start fresh
- No cross-region session migration — session is pinned to the region where it started

---

## ADR-007: Kafka for Telemetry and Inter-Service Events

**Status:** Accepted

**Context:** Need to emit structured events for analytics (Project C), audit logging, and real-time monitoring. Events must be durable and consumable by multiple downstream services.

**Decision:** Use Kafka (Redpanda) with 4 event topics for structured telemetry.

**Rationale:**
- Decouples event producers (voice pipeline, agents) from consumers (analytics, monitoring)
- Durable log enables replay for debugging and backfill
- 4 focused topics (`hsv.intents`, `hsv.tools`, `hsv.sessions`, `hsv.escalations`) keep schemas clean
- Redpanda is Kafka-compatible with lower operational overhead and better single-node performance
- Consumer groups enable independent processing — analytics and monitoring scale separately

**Consequences:**
- Additional infrastructure component to operate (mitigated by Redpanda Cloud managed service)
- Event schemas must be evolved carefully — no schema registry yet (JSON-only)
- Adds ~2-5ms per event publish — acceptable for non-critical-path telemetry

---

## ADR-008: multilingual-MiniLM-L6-v2 for Intent Classification

**Status:** Accepted

**Context:** Need to classify Hausa and English utterances into intents (balance, transfer, bills, general) with code-switching support. Must run locally for low latency.

**Decision:** Use `sentence-transformers/paraphrase-multilingual-MiniLM-L6-v2` for intent classification via cosine similarity against intent embeddings.

**Rationale:**
- Supports 50+ languages including Hausa — handles code-switching naturally
- 22M parameters, ~5ms inference on CPU — well within latency budget
- Embedding-based classification avoids fine-tuning per intent — add new intents by adding example sentences
- No API call required — runs locally, zero marginal cost
- Model size (~90MB) fits comfortably in container image

**Consequences:**
- Classification quality depends on the quality of intent example sentences
- May struggle with very similar intents — confidence thresholds need tuning
- No online learning — intent examples are static (update requires redeployment)

---

## ADR-009: uv over pip/Poetry for Package Management

**Status:** Accepted

**Context:** Need a Python package manager that is fast, reproducible, and simple for a team working with Python 3.12+ and strict dependency pinning.

**Decision:** Use `uv` for all package management — replace pip, pip-tools, and Poetry.

**Rationale:**
- **10–100× faster** than pip for installs and resolution (Rust-based resolver)
- Deterministic lockfile (`uv.lock`) pins every transitive dependency — bit-for-bit reproducible builds
- No virtualenv activation needed — `uv run` handles environment automatically
- Single tool replaces pip + pip-tools + virtualenv + Poetry — simpler CI and developer setup
- `uv sync` from lockfile is near-instant in CI (cached resolution)
- Growing ecosystem adoption and active development (Astral)

**Consequences:**
- Team must use `uv add` / `uv remove` instead of `pip install` — muscle memory adjustment
- Some edge cases with packages that have non-standard build systems (rare with Python 3.12+)
- Lockfile format is uv-specific — can't be consumed by pip directly (but `uv export` generates `requirements.txt` if needed)
