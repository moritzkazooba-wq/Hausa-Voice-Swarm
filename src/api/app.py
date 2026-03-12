"""FastAPI application with GraphQL, health, and metrics endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

# Import definitions to ensure metrics are registered at import time
import src.metrics.definitions as _metrics_defs  # noqa: F401
from src.api.schema import GraphQLContext, schema
from src.metrics.middleware import MetricsMiddleware

# Module-level readiness flag.
# Fine for single-worker dev; for production, replace with a DB check.
_ready: bool = False


class SimulateCallRequest(BaseModel):
    """Request body for /test/simulate-call."""

    phone_number: str
    text: str
    session_id: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle."""
    global _ready
    _ready = True
    yield
    _ready = False


def _get_context() -> GraphQLContext:
    """Create a fresh GraphQL context with DataLoaders per request."""
    return GraphQLContext()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Hausa Voice Swarm API",
        description="Voice agent system for mobile money customer support",
        lifespan=lifespan,
    )

    # Metrics middleware (must be added before CORS so it wraps all requests)
    app.add_middleware(MetricsMiddleware)

    # CORS — permissive for dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GraphQL
    graphql_router = GraphQLRouter[Any, None](
        schema,
        context_getter=_get_context,
    )
    app.include_router(graphql_router, prefix="/graphql")

    # Health check
    @app.get("/health")
    async def health() -> JSONResponse:
        if not _ready:
            return JSONResponse({"status": "starting"}, status_code=503)
        return JSONResponse({"status": "ok"})

    # Prometheus metrics endpoint
    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(
            generate_latest().decode("utf-8"),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Simulate-call stub (wired to real pipeline in Phase 7a)
    @app.post("/test/simulate-call")
    async def simulate_call(req: SimulateCallRequest) -> JSONResponse:
        return JSONResponse(
            {
                "response": "Pipeline not yet connected",
                "session_id": req.session_id or "stub",
            }
        )

    return app
