"""FastAPI application with GraphQL, health, and metrics endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

from src.api.schema import GraphQLContext, schema

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

    # Metrics placeholder (wired in Phase 6)
    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse("")

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
