"""Prometheus metric definitions for Hausa Voice Swarm."""

from prometheus_client import Counter, Gauge, Histogram

# ── Session metrics ──────────────────────────────────────────────────

active_voice_sessions = Gauge(
    "hsv_active_voice_sessions",
    "Number of currently active voice sessions",
)

session_duration_seconds = Histogram(
    "hsv_session_duration_seconds",
    "Duration of voice sessions in seconds",
    buckets=(5, 15, 30, 60, 120, 300, 600, 1800),
)

# ── Latency metrics ─────────────────────────────────────────────────

voice_to_voice_latency_ms = Histogram(
    "hsv_voice_to_voice_latency_ms",
    "End-to-end voice-to-voice latency in milliseconds",
    buckets=(100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000),
)

asr_latency_ms = Histogram(
    "hsv_asr_latency_ms",
    "ASR processing latency in milliseconds",
    labelnames=("model", "intent"),
    buckets=(50, 100, 200, 500, 1000, 2000),
)

tts_latency_ms = Histogram(
    "hsv_tts_latency_ms",
    "TTS processing latency in milliseconds",
    labelnames=("model", "intent"),
    buckets=(50, 100, 200, 500, 1000, 2000),
)

llm_latency_ms = Histogram(
    "hsv_llm_latency_ms",
    "LLM call latency in milliseconds",
    labelnames=("model", "intent"),
    buckets=(100, 250, 500, 1000, 2000, 5000, 10000),
)

# ── Agent / routing metrics ──────────────────────────────────────────

intent_classification_total = Counter(
    "hsv_intent_classification_total",
    "Total intent classifications",
    labelnames=("intent", "classifier_type"),
)

tool_execution_total = Counter(
    "hsv_tool_execution_total",
    "Total tool executions by domain agents",
    labelnames=("tool_name", "success"),
)

agent_routing_total = Counter(
    "hsv_agent_routing_total",
    "Total agent routing decisions by the supervisor",
    labelnames=("target_agent",),
)

# ── Cost metrics ─────────────────────────────────────────────────────

cost_per_interaction_usd = Histogram(
    "hsv_cost_per_interaction_usd",
    "Estimated cost per interaction in USD",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# ── HTTP metrics (populated by MetricsMiddleware) ────────────────────

http_requests_total = Counter(
    "hsv_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status_code"),
)

http_request_duration_ms = Histogram(
    "hsv_http_request_duration_ms",
    "HTTP request duration in milliseconds",
    labelnames=("method", "path"),
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500),
)
