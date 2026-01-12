"""Logger factory functions for different application layers."""

import structlog


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


def get_security_logger():
    """Get the security logger for backwards compatibility."""
    return get_logger("roadmap.security")
