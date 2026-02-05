"""Service for handling sync authentication with pluggable backends.

Updated to use Result<T, SyncError> pattern for explicit error handling.
"""

from structlog import get_logger

from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.services.sync.sync_report import SyncReport

logger = get_logger(__name__)


class SyncAuthenticationService:
    """Handles backend authentication for sync operations."""

    def __init__(self, backend: SyncBackendInterface):
        """Initialize authentication service.

        Args:
            backend: SyncBackendInterface implementation
        """
        self.backend = backend

    def ensure_authenticated(self, report: SyncReport) -> bool:
        """Ensure backend is authenticated.

        Args:
            report: SyncReport to record any authentication errors

        Returns:
            True if authenticated, False otherwise

        Notes:
            Handles Result<bool, SyncError> from backend.authenticate()
        """
        result = self.backend.authenticate()

        if result.is_ok():
            logger.info("backend_authenticated_successfully")
            return True

        # Handle authentication error
        error = result.unwrap_err()
        report.error = str(error)

        logger.error(
            "backend_authentication_failed",
            operation="authenticate",
            backend_type=type(self.backend).__name__,
            error_type=error.error_type.value,
            error_message=error.message,
            is_recoverable=error.is_recoverable,
            suggested_action=error.suggested_fix or "check_credentials",
        )

        return False
