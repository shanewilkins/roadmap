"""Security event logging utilities."""

from datetime import UTC, datetime
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
