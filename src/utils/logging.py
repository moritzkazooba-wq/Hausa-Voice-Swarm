"""structlog configuration for structured JSON logging."""

import structlog


def configure_logging() -> None:
    """Configure structlog with JSON output for production.

    Call once at application startup (e.g. in FastAPI lifespan).
    Safe to call multiple times — uses cache_logger_on_first_use.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
