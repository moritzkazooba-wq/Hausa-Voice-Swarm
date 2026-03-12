"""WebSocket server for telephony audio streams.

Stub server that logs connections. Real transport wiring in future phase.
Started/stopped via FastAPI lifespan context manager.
"""

from __future__ import annotations

import asyncio

import structlog
import websockets.asyncio.server

logger = structlog.get_logger()


async def start_ws_server(port: int = 8765) -> asyncio.Server:
    """Start the WebSocket server for audio streams.

    Currently a stub that logs connections without processing audio.
    Real transport wiring happens when Daily/Telnyx integration is added.
    """

    async def handler(
        websocket: websockets.asyncio.server.ServerConnection,
    ) -> None:
        remote = websocket.remote_address
        await logger.ainfo("ws_connected", remote=str(remote))
        try:
            async for msg in websocket:
                size = len(msg) if isinstance(msg, (bytes, str)) else 0
                await logger.adebug("ws_message_received", size=size)
        except websockets.exceptions.ConnectionClosed:
            await logger.ainfo("ws_disconnected", remote=str(remote))

    server = await websockets.asyncio.server.serve(
        handler,
        "0.0.0.0",  # noqa: S104
        port,
    )
    await logger.ainfo("ws_server_started", port=port)
    return server  # type: ignore[return-value]
