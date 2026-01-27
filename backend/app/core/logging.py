"""Structured logging configuration using structlog."""
import logging
import structlog
from structlog.processors import (
    TimeStamper,
    add_log_level,
    StackInfoRenderer,
    format_exc_info,
)
from structlog.dev import ConsoleRenderer
from structlog.stdlib import (
    ProcessorFormatter,
    add_logger_name,
    filter_by_level,
)


def configure_logging(environment: str = "production") -> None:
    """
    Configure structured logging with JSON output.

    Args:
        environment: "development" for console output, "production" for JSON
    """
    # Shared processors for all handlers
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        add_logger_name,
        StackInfoRenderer(),
        format_exc_info,
        TimeStamper(fmt="iso"),
    ]

    if environment == "development":
        # Development: human-readable console output
        processors = shared_processors + [ConsoleRenderer()]
        formatter = ProcessorFormatter(
            processor=ConsoleRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        # Production: JSON output
        processors = shared_processors + [structlog.processors.JSONRenderer()]
        formatter = ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to work with structlog
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger():
    """Get a structlog logger instance."""
    return structlog.get_logger()
