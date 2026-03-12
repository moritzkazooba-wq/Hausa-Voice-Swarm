"""Tests for Prometheus metric definitions and instrumentation."""

from __future__ import annotations

from prometheus_client import REGISTRY
from src.metrics.definitions import (
    active_voice_sessions,
    agent_routing_total,
    asr_latency_ms,
    cost_per_interaction_usd,
    http_request_duration_ms,
    http_requests_total,
    intent_classification_total,
    llm_latency_ms,
    session_duration_seconds,
    tool_execution_total,
    tts_latency_ms,
    voice_to_voice_latency_ms,
)


def test_all_metrics_registered() -> None:
    """All custom metrics should be registered in the default registry."""
    # Collect metric family names (without _total/_bucket suffixes)
    registered_names: set[str] = set()
    for collector in REGISTRY.collect():
        for sample in collector.samples:
            registered_names.add(sample.name)

    # Gauges and unlabeled histograms emit samples immediately;
    # labeled counters/histograms only after first use. Check a mix.
    assert "hsv_active_voice_sessions" in registered_names

    # Trigger labeled metrics so they appear in the registry
    intent_classification_total.labels(intent="test", classifier_type="test").inc()
    tool_execution_total.labels(tool_name="test", success="True").inc()
    agent_routing_total.labels(target_agent="test").inc()
    http_requests_total.labels(method="GET", path="/test", status_code="200").inc()

    refreshed = {s.name for c in REGISTRY.collect() for s in c.samples}
    for name in (
        "hsv_active_voice_sessions",
        "hsv_intent_classification_total",
        "hsv_tool_execution_total",
        "hsv_agent_routing_total",
        "hsv_http_requests_total",
    ):
        assert name in refreshed, f"{name} not found in registry"


def test_gauge_increment_decrement() -> None:
    """active_voice_sessions gauge should support inc/dec."""
    before = active_voice_sessions._value.get()
    active_voice_sessions.inc()
    assert active_voice_sessions._value.get() == before + 1
    active_voice_sessions.dec()
    assert active_voice_sessions._value.get() == before


def test_intent_counter_labels() -> None:
    """intent_classification_total should accept intent and classifier_type labels."""
    intent_classification_total.labels(
        intent="balance", classifier_type="sentence-transformers"
    ).inc()
    val = intent_classification_total.labels(
        intent="balance", classifier_type="sentence-transformers"
    )._value.get()
    assert val >= 1


def test_tool_execution_counter_labels() -> None:
    """tool_execution_total should accept tool_name and success labels."""
    tool_execution_total.labels(tool_name="balance", success="True").inc()
    val = tool_execution_total.labels(tool_name="balance", success="True")._value.get()
    assert val >= 1


def test_agent_routing_counter() -> None:
    """agent_routing_total should accept target_agent label."""
    agent_routing_total.labels(target_agent="transfer").inc()
    val = agent_routing_total.labels(target_agent="transfer")._value.get()
    assert val >= 1


def test_histogram_observe() -> None:
    """Latency histograms should accept observations."""
    voice_to_voice_latency_ms.observe(500.0)
    session_duration_seconds.observe(120.0)
    cost_per_interaction_usd.observe(0.01)
    # No exception means success


def test_labeled_histogram_observe() -> None:
    """Labeled latency histograms should accept observations."""
    asr_latency_ms.labels(model="whisper-hausa", intent="balance").observe(150.0)
    tts_latency_ms.labels(model="coqui", intent="balance").observe(200.0)
    llm_latency_ms.labels(model="gpt-4o", intent="transfer").observe(800.0)


def test_http_metrics() -> None:
    """HTTP metrics should accept method/path/status labels."""
    http_requests_total.labels(method="GET", path="/health", status_code="200").inc()
    http_request_duration_ms.labels(method="GET", path="/health").observe(5.0)
