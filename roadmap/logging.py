"""Structured logging configuration for roadmap CLI application."""

import logging
import logging.config
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str | Path | None = None,
    debug_mode: bool = False,
) -> structlog.stdlib.BoundLogger:
    """Set up structured logging for the roadmap application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
        log_dir: Directory for log files (defaults to ~/.roadmap/logs)
        debug_mode: Enable debug mode with verbose output

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

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
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
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"] if not log_to_file else [],
        },
    }

    logging.config.dictConfig(config)

    # Configure structlog
    structlog.configure(
        processors=[
            # Add caller information
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


def get_logger(name: str = "roadmap") -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_operation(operation: str, **context):
    """Decorator for logging operation start/end with context.

    Args:
        operation: Operation name
        **context: Additional context to log
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            logger.info(f"Starting {operation}", **context)
            try:
                result = func(*args, **kwargs)
                logger.info(f"Completed {operation}", **context)
                return result
            except Exception as e:
                logger.error(
                    f"Failed {operation}",
                    error=str(e),
                    error_type=type(e).__name__,
                    **context,
                )
                raise

        return wrapper

    return decorator


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
