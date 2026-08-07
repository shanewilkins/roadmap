"""Base class for all health validators.

Provides consistent error handling, logging, and status reporting patterns
for health check validators throughout the application.

All validators should inherit from BaseValidator and implement:
- get_check_name(): Return unique check identifier
- perform_check(): Return (status, message) tuple

The base class handles error handling and logging automatically.
"""

from abc import ABC, abstractmethod

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class HealthStatus:
    """Health status constants for validator responses."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class BaseValidator(ABC):
    """Abstract base class for all health validators.

    Provides:
    - Consistent error handling and logging
    - Standard status/message return format
    - Simplified subclass implementation (business logic only)

    Subclasses should override:
    - get_check_name(): Return the unique name of this check
    - perform_check(): Return (status, message) tuple or raise exceptions

    The check() method wraps perform_check() with try/except, logging,
    and error handling so subclasses focus on business logic only.

    Example:
        class RoadmapDirectoryValidator(BaseValidator):
            @staticmethod
            def get_check_name() -> str:
                return "roadmap_directory"

            @staticmethod
            def perform_check() -> Tuple[str, str]:
                roadmap_dir = Path(".roadmap")
                if not roadmap_dir.exists():
                    return HealthStatus.DEGRADED, ".roadmap not found"

                try:
                    test_file = roadmap_dir / ".test"
                    test_file.touch()
                    test_file.unlink()
                except OSError:
                    return HealthStatus.DEGRADED, "Directory not writable"

                return HealthStatus.HEALTHY, "Accessible and writable"

        # Usage:
        status, message = RoadmapDirectoryValidator.check()
    """

    @staticmethod
    @abstractmethod
    def get_check_name() -> str:
        """Return the unique name of this check.

        Returns:
            Check name as string (e.g., "roadmap_directory", "git_repository")
        """
        pass

    @staticmethod
    @abstractmethod
    def perform_check() -> tuple[str, str]:
        """Perform the actual check logic.

        Should return a tuple of (status, message) where:
        - status is one of: HealthStatus.HEALTHY, .DEGRADED, .UNHEALTHY
        - message is a human-readable description

        May raise exceptions for error conditions. The check() method
        will catch them and return UNHEALTHY status.

        Returns:
            Tuple of (status, message)

        Raises:
            Any exception on error conditions (will be caught and logged)
        """
        pass

    @classmethod
    def check(cls) -> tuple[str, str]:
        """Execute the check with standard error handling and logging.

        Wraps perform_check() with:
        - Exception handling
        - Automatic logging at appropriate levels
        - Error context enrichment
        - Consistent status reporting

        Returns:
            Tuple of (status, message)
        """
        try:
            status, message = cls.perform_check()
            logger.debug(
                "health_check_completed",
                check_name=cls.get_check_name(),
                status=status,
            )
            return status, message
        except Exception as e:
            logger.error(
                "health_check_failed",
                check_name=cls.get_check_name(),
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            return (
                HealthStatus.UNHEALTHY,
                f"Error checking {cls.get_check_name()}: {e}",
            )
