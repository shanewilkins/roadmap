"""Security event logging utilities."""

import logging
from pathlib import Path
from typing import Any

# Security logger
security_logger = logging.getLogger("roadmap.security")


def log_security_event(event_type: str, details: dict[str, Any] | None = None) -> None:
    """Log a security event with structured data.

    Args:
        event_type: Type of security event
        details: Additional event details
    """
    if details is None:
        details = {}

    try:
        # Add timestamp and event type to details
        log_data = {
            "event_type": event_type,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            **details,
        }

        # Only log if the logger has handlers and they're not closed
        if security_logger.handlers:
            # Check if handlers are still valid
            for handler in security_logger.handlers:
                if hasattr(handler, "stream") and hasattr(handler, "stream"):
                    stream = getattr(handler, "stream", None)
                    if stream and hasattr(stream, "closed") and stream.closed:
                        return  # Skip logging if stream is closed

        # Log as structured data
        security_logger.info(f"Security event: {event_type}", extra=log_data)

    except Exception:
        # Don't let logging failures break functionality
        pass


def configure_security_logging(
    log_level: str = "INFO", log_file: Path | None = None
) -> None:
    """Configure security event logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to log to (in addition to console)
    """
    # Set up security logger
    security_logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    security_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        security_logger.addHandler(file_handler)

        # Secure the log file - import here to avoid circular dependency
        from .file_operations import secure_file_permissions

        secure_file_permissions(log_file, 0o600)
