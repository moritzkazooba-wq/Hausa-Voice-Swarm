"""FastAPI middleware for Prometheus HTTP metrics."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.metrics.definitions import http_request_duration_ms, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request count and latency as Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000.0

        path = request.url.path
        method = request.method
        status = str(response.status_code)

        http_requests_total.labels(method=method, path=path, status_code=status).inc()
        http_request_duration_ms.labels(method=method, path=path).observe(elapsed_ms)

        return response
