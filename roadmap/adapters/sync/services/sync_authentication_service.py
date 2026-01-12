"""Service for handling sync authentication with pluggable backends."""

from structlog import get_logger

from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.services.sync_report import SyncReport

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
        """
        try:
            if not self.backend.authenticate():
                report.error = "Backend authentication failed"
                logger.error(
                    "backend_authentication_failed",
                    operation="authenticate",
                    backend_type=type(self.backend).__name__,
                    suggested_action="check_credentials",
                )
                return False
            logger.info("backend_authenticated_successfully")
            return True
        except (ConnectionError, TimeoutError) as e:
            report.error = f"Backend authentication error: {str(e)}"
            logger.error(
                "backend_authentication_error",
                operation="authenticate",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="retry_connection",
            )
            return False
        except Exception as e:
            report.error = f"Backend authentication error: {str(e)}"
            logger.error(
                "backend_authentication_error",
                operation="authenticate",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_backend_status",
            )
            return False
