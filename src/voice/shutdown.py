"""Graceful shutdown handler for voice sessions.

SIGTERM → toggle /health to 503 → wait for active sessions (5 min max)
→ persist remaining sessions to Redis with 1-hour TTL → exit.
"""

from __future__ import annotations

import asyncio
import signal

import structlog

from src.voice.session_manager import SessionManager

logger = structlog.get_logger()

_MAX_DRAIN_SECONDS = 300  # 5 minutes max wait
_DRAIN_POLL_INTERVAL = 1.0  # Check every second


class GracefulShutdown:
    """Coordinates graceful shutdown of voice sessions.

    On SIGTERM:
    1. Sets shutting_down flag (health endpoint returns 503)
    2. Waits up to max_drain_seconds for active sessions to drain
    3. Persists any remaining sessions to Redis with 1-hour TTL
    4. Sets the shutdown_complete event so the app can exit
    """

    def __init__(
        self,
        session_manager: SessionManager,
        *,
        max_drain_seconds: float = _MAX_DRAIN_SECONDS,
    ) -> None:
        self._session_manager = session_manager
        self._max_drain_seconds = max_drain_seconds
        self._shutting_down = False
        self._shutdown_complete = asyncio.Event()
        self._drain_task: asyncio.Task[None] | None = None

    @property
    def is_shutting_down(self) -> bool:
        """Whether shutdown has been initiated."""
        return self._shutting_down

    @property
    def shutdown_complete(self) -> asyncio.Event:
        """Event that is set when shutdown is fully complete."""
        return self._shutdown_complete

    def install_signal_handlers(self) -> None:
        """Install SIGTERM and SIGINT handlers on the running event loop."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._on_signal, sig)

    def _on_signal(self, sig: signal.Signals) -> None:
        """Handle termination signal — starts async drain."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self._drain_task = asyncio.create_task(self._drain_and_persist())

    async def _drain_and_persist(self) -> None:
        """Wait for sessions to drain, then persist remaining."""
        await logger.ainfo(
            "shutdown_initiated",
            active_sessions=self._session_manager.active_count,
        )

        # Wait for active sessions to complete
        elapsed = 0.0
        while (
            self._session_manager.active_count > 0
            and elapsed < self._max_drain_seconds
        ):
            await asyncio.sleep(_DRAIN_POLL_INTERVAL)
            elapsed += _DRAIN_POLL_INTERVAL
            if int(elapsed) % 10 == 0:
                await logger.ainfo(
                    "shutdown_draining",
                    remaining=self._session_manager.active_count,
                    elapsed_s=int(elapsed),
                )

        # Persist any remaining sessions with extended TTL
        remaining = self._session_manager.active_sessions
        if remaining:
            await logger.awarning(
                "shutdown_persisting_sessions",
                count=len(remaining),
            )
            for session_id in remaining:
                await self._session_manager.persist_for_shutdown(session_id)

        await logger.ainfo("shutdown_complete")
        self._shutdown_complete.set()

    async def wait_for_shutdown(self) -> None:
        """Block until shutdown is fully complete."""
        await self._shutdown_complete.wait()
