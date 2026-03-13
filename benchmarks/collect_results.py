#!/usr/bin/env python3
"""Collect Prometheus metrics after a k6 run and generate a markdown report.

Usage:
    python benchmarks/collect_results.py [--prometheus URL] [--output FILE]

Defaults:
    --prometheus  http://localhost:9090
    --output      benchmarks/report.md
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen
import json


def _query(base_url: str, expr: str) -> list[dict[str, object]]:
    """Run an instant PromQL query and return the result vector."""
    from urllib.parse import quote

    url = f"{base_url}/api/v1/query?query={quote(expr)}"
    try:
        with urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except (URLError, OSError) as exc:
        print(f"  ⚠ Could not reach Prometheus at {base_url}: {exc}", file=sys.stderr)
        return []

    if data.get("status") != "success":
        print(f"  ⚠ Query failed: {expr}", file=sys.stderr)
        return []

    return data.get("data", {}).get("result", [])


def _scalar(results: list[dict[str, object]]) -> str:
    """Extract a single scalar value from a Prometheus result vector."""
    if not results:
        return "N/A"
    value = results[0].get("value", [None, "N/A"])
    if isinstance(value, list) and len(value) >= 2:
        raw = value[1]
        try:
            return f"{float(str(raw)):.2f}"
        except (ValueError, TypeError):
            return str(raw)
    return "N/A"


def _histogram_quantile(
    base_url: str, metric: str, quantile: float, window: str = "10m"
) -> str:
    """Compute a histogram quantile from Prometheus."""
    expr = f'histogram_quantile({quantile}, rate({metric}_bucket[{window}]))'
    return _scalar(_query(base_url, expr))


def collect(base_url: str) -> dict[str, str]:
    """Collect key metrics from Prometheus."""
    metrics: dict[str, str] = {}

    # Active sessions
    metrics["active_sessions"] = _scalar(
        _query(base_url, "hsv_active_voice_sessions")
    )

    # Voice-to-voice latency percentiles
    for q, label in [(0.50, "p50"), (0.95, "p95"), (0.99, "p99")]:
        metrics[f"v2v_latency_{label}"] = _histogram_quantile(
            base_url, "hsv_voice_to_voice_latency_ms", q
        )

    # HTTP request rate
    metrics["http_rps"] = _scalar(
        _query(base_url, 'rate(hsv_http_requests_total[5m])')
    )

    # HTTP latency p95
    metrics["http_p95"] = _histogram_quantile(
        base_url, "hsv_http_request_duration_ms", 0.95, "5m"
    )

    # Total intent classifications
    metrics["total_intents"] = _scalar(
        _query(base_url, "hsv_intent_classification_total")
    )

    # Agent routing totals by agent
    routing = _query(
        base_url,
        'sum by (target_agent) (hsv_agent_routing_total)',
    )
    for result in routing:
        agent = result.get("metric", {}).get("target_agent", "unknown")
        val = result.get("value", [None, "0"])
        count = val[1] if isinstance(val, list) and len(val) >= 2 else "0"
        metrics[f"routing_{agent}"] = str(count)

    # Error rate (HTTP 5xx)
    metrics["error_rate"] = _scalar(
        _query(
            base_url,
            'sum(rate(hsv_http_requests_total{status_code=~"5.."}[5m]))'
            ' / sum(rate(hsv_http_requests_total[5m]))',
        )
    )

    return metrics


def render_report(metrics: dict[str, str]) -> str:
    """Render collected metrics as a markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Load Test Report",
        "",
        f"**Generated:** {now}",
        "",
        "## Voice-to-Voice Latency",
        "",
        "| Percentile | Latency (ms) |",
        "|-----------|-------------|",
        f"| p50       | {metrics.get('v2v_latency_p50', 'N/A')} |",
        f"| p95       | {metrics.get('v2v_latency_p95', 'N/A')} |",
        f"| p99       | {metrics.get('v2v_latency_p99', 'N/A')} |",
        "",
        "## HTTP Metrics",
        "",
        f"- **Request rate:** {metrics.get('http_rps', 'N/A')} req/s",
        f"- **HTTP p95 latency:** {metrics.get('http_p95', 'N/A')} ms",
        f"- **Error rate (5xx):** {metrics.get('error_rate', 'N/A')}",
        "",
        "## Agent Routing",
        "",
        f"- **Active sessions:** {metrics.get('active_sessions', 'N/A')}",
        f"- **Total classifications:** {metrics.get('total_intents', 'N/A')}",
        "",
        "| Agent | Requests |",
        "|-------|----------|",
    ]

    for key, value in sorted(metrics.items()):
        if key.startswith("routing_"):
            agent = key.removeprefix("routing_")
            lines.append(f"| {agent} | {value} |")

    lines.extend(["", "---", ""])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect load test results")
    parser.add_argument(
        "--prometheus",
        default="http://localhost:9090",
        help="Prometheus base URL",
    )
    parser.add_argument(
        "--output",
        default="benchmarks/report.md",
        help="Output markdown file",
    )
    args = parser.parse_args()

    print(f"Collecting metrics from {args.prometheus} ...")
    metrics = collect(args.prometheus)
    report = render_report(metrics)

    with open(args.output, "w") as f:
        f.write(report)

    print(f"Report written to {args.output}")
    print()
    print(report)


if __name__ == "__main__":
    main()
