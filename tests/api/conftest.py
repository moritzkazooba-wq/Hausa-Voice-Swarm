"""API test fixtures — consolidated app and client for endpoint / GraphQL tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import src.api.app as app_module
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from src.api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    """Create a fresh FastAPI application instance."""
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client bound to the app (lifespan bypassed via _ready flag)."""
    app_module._ready = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app_module._ready = False
