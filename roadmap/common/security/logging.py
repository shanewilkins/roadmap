"""Security event logging utilities."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from structlog import get_logger

# Security logger
security_logger = get_logger()


def log_security_event(event_type: str, details: dict[str, Any] | None = None) -> None:
    """Log a security event with structured data.

    Args:
        event_type: Type of security event
        details: Additional event details
    """
    if details is None:
        details = {}

    # Log as structured data
    security_logger.info(
        event_type,
        timestamp=datetime.now(UTC).isoformat(),
        **details,
    )


def configure_security_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,  # noqa: ARG001
) -> None:
    """Configure security event logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to log to (in addition to console)
    """
    # Structlog configuration is centralized in roadmap/common/logging/__init__.py
    # This function is kept for backward compatibility
    pass
