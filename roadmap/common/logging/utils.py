"""Logging setup and utility functions."""

import logging
import logging.config
import logging.handlers
import random
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import structlog

from roadmap.common.logging.correlation import add_correlation_id
from roadmap.common.logging.formatters import (
    include_structured_fields_in_message,
    scrub_sensitive_data,
)
from roadmap.shared.instrumentation import span_context_processor


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str | Path | None = None,
    debug_mode: bool = False,
    console_level: str | None = None,
    custom_levels: dict[str, str] | None = None,
) -> structlog.stdlib.BoundLogger:
    """Set up structured logging for the roadmap application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
        log_dir: Directory for log files (defaults to .roadmap/logs in current working directory)
        debug_mode: Enable debug mode with verbose output
        console_level: Override console handler level (e.g., "INFO" for --verbose)
                      If None, defaults to DEBUG if debug_mode else WARNING
        custom_levels: Dict of logger_name: level for per-component log levels

    Returns:
        Configured structlog logger
    """
    if log_dir is None:
        log_dir = Path.cwd() / ".roadmap" / "logs"
    else:
        log_dir = Path(log_dir)

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "roadmap.log"

    # Configure standard library logging
    # Use explicit sys.stderr for console to ensure logs go to stderr, not stdout
    # Determine console level: explicit override > debug_mode > default WARNING
    if console_level is None:
        console_level = "DEBUG" if debug_mode else "WARNING"

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": console_level,
            "formatter": "console",
            "stream": "ext://sys.stderr",  # Explicitly use stderr
        }
    }

    formatters = {
        "console": {
            "format": "%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%SZ",
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
            "handlers": list(handlers.keys()),  # Use all configured handlers
        },
    }

    logging.config.dictConfig(config)

    # Configure structlog with enhanced processors
    # Route through stdlib logging handlers (console → stderr, file → JSON)
    processors: list = [
        # Add correlation ID first (before any filtering)
        add_correlation_id,
        # Add span context for tracing
        span_context_processor,
        # Scrub sensitive data early in pipeline
        scrub_sensitive_data,
        # Add standard metadata
        structlog.stdlib.add_log_level,
        # NOTE: Do NOT use add_logger_name when using render_to_log_kwargs
        # because it creates a "logger" key that becomes "name" kwarg in LogRecord,
        # causing: KeyError: "Attempt to overwrite 'name' in LogRecord"
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        # Include structured fields in message for visibility
        include_structured_fields_in_message,
        # Convert to stdlib logging kwargs and pass through to handlers
        structlog.stdlib.render_to_log_kwargs,
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("roadmap")


def get_stack_trace(depth: int = 5) -> str:
    """Get a formatted stack trace for DEBUG logging.

    This utility makes it easy to add rich context to DEBUG logs without
    cluttering the normal code path. Stack traces help with troubleshooting
    unexpected behavior and finding where operations are triggered from.

    Args:
        depth: Number of stack frames to include (default 5)

    Returns:
        Formatted multi-line stack trace suitable for log output

    Example:
        logger = get_logger(__name__)
        logger.debug(
            "operation_triggered",
            operation="sync",
            stack=get_stack_trace()
        )
    """
    stack_lines = traceback.format_stack()[:-1]  # Exclude this function
    # Get the last 'depth' frames
    relevant_lines = stack_lines[-depth:]
    formatted = "\n  ".join([line.strip() for line in relevant_lines])
    return formatted


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
    from roadmap.common.logging.loggers import get_logger

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
    from roadmap.common.logging.loggers import get_logger

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


def configure_for_testing():
    """Configure minimal logging for tests."""
    logging.basicConfig(level=logging.CRITICAL)
    structlog.configure(
        processors=[
            # Minimal processors for testing
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # Use PrintLogger for simple output
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
