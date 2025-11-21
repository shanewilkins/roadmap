"""Structured logging configuration for roadmap CLI application."""

import contextvars
import logging
import logging.config
import logging.handlers
import random
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import structlog

# Context variable for correlation ID tracking across async operations
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Sensitive keys that should be redacted from logs
SENSITIVE_KEYS = {
    "token",
    "password",
    "secret",
    "api_key",
    "auth",
    "credential",
    "github_token",
}


def add_correlation_id(logger, method_name, event_dict):
    """Structlog processor to add correlation ID to all log entries."""
    cid = correlation_id_var.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def scrub_sensitive_data(logger, method_name, event_dict):
    """Structlog processor to remove sensitive data from logs."""

    def scrub_value(key, value):
        """Recursively scrub sensitive values."""
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            return "***REDACTED***"
        if isinstance(value, dict):
            return {k: scrub_value(k, v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return type(value)(scrub_value(f"item_{i}", v) for i, v in enumerate(value))
        return value

    return {k: scrub_value(k, v) for k, v in event_dict.items()}


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str | Path | None = None,
    debug_mode: bool = False,
    custom_levels: dict[str, str] | None = None,
) -> structlog.stdlib.BoundLogger:
    """Set up structured logging for the roadmap application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
        log_dir: Directory for log files (defaults to ~/.roadmap/logs)
        debug_mode: Enable debug mode with verbose output
        custom_levels: Dict of logger_name: level for per-component log levels

    Returns:
        Configured structlog logger
    """
    if log_dir is None:
        log_dir = Path.home() / ".roadmap" / "logs"
    else:
        log_dir = Path(log_dir)

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "roadmap.log"

    # Configure standard library logging
    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING" if not debug_mode else "DEBUG",
            "formatter": "console",
            "stream": sys.stderr,
        }
    }

    formatters = {
        "console": {
            "format": "%(message)s"  # Rich console handles formatting
        }
    }

    if log_to_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "structured",
            "filename": str(log_file),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }

        formatters["structured"] = {
            "format": "%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }

    # Build logger configuration with custom levels support
    loggers_config = {
        "roadmap": {
            "level": log_level,
            "handlers": list(handlers.keys()),
            "propagate": False,
        },
        "roadmap.security": {
            "level": "INFO",
            "handlers": list(handlers.keys()),
            "propagate": False,
        },
        # Suppress noisy third-party loggers
        "urllib3": {"level": "WARNING"},
        "requests": {"level": "WARNING"},
        "aiohttp": {"level": "WARNING"},
        "git": {"level": "WARNING"},
    }

    # Add custom per-component log levels
    if custom_levels:
        for logger_name, level in custom_levels.items():
            full_name = (
                f"roadmap.{logger_name}"
                if not logger_name.startswith("roadmap.")
                else logger_name
            )
            loggers_config[full_name] = {
                "level": level.upper(),
                "handlers": list(handlers.keys()),
                "propagate": False,
            }

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers_config,
        "root": {
            "level": "WARNING",
            "handlers": ["console"] if not log_to_file else [],
        },
    }

    logging.config.dictConfig(config)

    # Configure structlog with enhanced processors
    structlog.configure(
        processors=[
            # Add correlation ID first (before any filtering)
            add_correlation_id,
            # Scrub sensitive data early in pipeline
            scrub_sensitive_data,
            # Add standard metadata
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            # Processor chain for console output
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
            if not log_to_file or debug_mode
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("roadmap")


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID for current context.

    Args:
        correlation_id: Optional correlation ID (generates UUID if None)

    Returns:
        The correlation ID that was set
    """
    cid = correlation_id or str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str | None:
    """Get correlation ID from current context.

    Returns:
        Current correlation ID or None
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)


def get_logger(name: str = "roadmap") -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def get_domain_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get logger for domain layer.

    Args:
        name: Component name (e.g., "issue", "milestone")

    Returns:
        Logger with domain namespace
    """
    return get_logger(f"roadmap.domain.{name}")


def get_application_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get logger for application layer.

    Args:
        name: Component name (e.g., "issue_service", "sync_service")

    Returns:
        Logger with application namespace
    """
    return get_logger(f"roadmap.application.{name}")


def get_infrastructure_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get logger for infrastructure layer.

    Args:
        name: Component name (e.g., "github", "storage")

    Returns:
        Logger with infrastructure namespace
    """
    return get_logger(f"roadmap.infrastructure.{name}")


def get_presentation_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get logger for presentation layer.

    Args:
        name: Component name (e.g., "cli.issues", "cli.milestones")

    Returns:
        Logger with presentation namespace
    """
    return get_logger(f"roadmap.presentation.{name}")


@contextmanager
def log_operation_timing(operation: str, logger=None, **context):
    """Context manager for timing and logging operations.

    Args:
        operation: Operation name
        logger: Optional logger (uses default if None)
        **context: Additional context to log

    Usage:
        with log_operation_timing("create_issue", issue_id="123"):
            core.create_issue(...)

    This will log:
        - Starting {operation} with context
        - Completed {operation} with duration and success status
        - Failed {operation} with duration and error details (on exception)
    """
    logger = logger or get_logger()
    start_time = time.perf_counter()

    logger.info(f"Starting {operation}", operation=operation, **context)

    try:
        yield
        duration = time.perf_counter() - start_time
        logger.info(
            f"Completed {operation}",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            success=True,
            **context,
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.error(
            f"Failed {operation}",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            success=False,
            error_type=type(e).__name__,
            error_message=str(e),
            **context,
        )
        raise


def log_operation(operation: str, **context):
    """Decorator for logging operation start/end with context and timing.

    Args:
        operation: Operation name
        **context: Additional context to log

    Usage:
        @log_operation("create_issue", issue_type="bug")
        def create_issue(...):
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = time.perf_counter()

            logger.info(f"Starting {operation}", operation=operation, **context)
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.info(
                    f"Completed {operation}",
                    operation=operation,
                    duration_ms=round(duration * 1000, 2),
                    success=True,
                    **context,
                )
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(
                    f"Failed {operation}",
                    operation=operation,
                    duration_ms=round(duration * 1000, 2),
                    success=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    **context,
                )
                raise

        return wrapper

    return decorator


def should_sample(sample_rate: float = 0.1) -> bool:
    """Determine if this log entry should be sampled.

    Args:
        sample_rate: Probability of sampling (0.0 to 1.0)
                    0.1 = 10% sampling, 0.01 = 1% sampling

    Returns:
        True if this entry should be logged

    Usage:
        if should_sample(sample_rate=0.01):  # 1% sampling
            logger.debug("Detailed operation info", ...)
    """
    return random.random() < sample_rate


# Initialize default logger (can be reconfigured later)
logger = structlog.get_logger("roadmap")


def configure_for_testing():
    """Configure minimal logging for tests."""
    logging.basicConfig(level=logging.CRITICAL)
    structlog.configure(
        processors=[structlog.testing.TestingRenderer()],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Backwards compatibility with existing security logger
def get_security_logger():
    """Get the security logger for backwards compatibility."""
    return get_logger("roadmap.security")
