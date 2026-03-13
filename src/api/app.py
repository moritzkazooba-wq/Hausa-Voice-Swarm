"""FastAPI application with GraphQL, health, and metrics endpoints."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

# Import definitions to ensure metrics are registered at import time
import src.metrics.definitions as _metrics_defs  # noqa: F401
from src.agents.supervisor import route_to_agent
from src.api.schema import GraphQLContext, schema
from src.config.settings import KafkaSettings, TelephonySettings
from src.events.producer import KafkaEventProducer
from src.metrics.definitions import active_voice_sessions, voice_to_voice_latency_ms
from src.metrics.middleware import MetricsMiddleware
from src.utils.logging import configure_logging
from src.voice.ws_server import start_ws_server

logger = structlog.get_logger()

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
    """Startup/shutdown lifecycle — logging, Kafka producer, WebSocket server."""
    global _ready

    configure_logging()

    settings = TelephonySettings()
    ws_server = await start_ws_server(settings.websocket_port)

    # Start Kafka event producer
    kafka_settings = KafkaSettings()
    producer = KafkaEventProducer(kafka_settings)
    try:
        await producer.start()
    except Exception:
        await logger.awarning("kafka_producer_start_failed", exc_info=True)
    app.state.kafka_producer = producer

    _ready = True
    await logger.ainfo("app_started", ws_port=settings.websocket_port)
    yield
    _ready = False

    # Shutdown
    try:
        await producer.stop()
    except Exception:
        await logger.awarning("kafka_producer_stop_failed", exc_info=True)
    ws_server.close()
    await ws_server.wait_closed()
    await logger.ainfo("app_stopped")


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
    graphql_router = GraphQLRouter[GraphQLContext, None](
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

    # Simulate-call — exercises the same agent routing as the voice pipeline
    @app.post("/test/simulate-call")
    async def simulate_call(req: SimulateCallRequest) -> JSONResponse:
        session_id = req.session_id or str(uuid4())

        active_voice_sessions.inc()
        start = time.monotonic()

        try:
            result, classification = await route_to_agent(
                session_id,
                req.text,
            )
        finally:
            active_voice_sessions.dec()

        latency_ms = (time.monotonic() - start) * 1000.0
        voice_to_voice_latency_ms.observe(latency_ms)

        return JSONResponse(
            {
                "response": result.message,
                "session_id": session_id,
                "intent": classification.intent,
                "latency_ms": round(latency_ms, 1),
            },
        )

    return app
