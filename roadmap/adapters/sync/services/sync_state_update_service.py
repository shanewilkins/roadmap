"""Service for tracking and updating baseline sync state."""

from datetime import UTC

from structlog import get_logger

from roadmap.core.services.sync.sync_state_manager import SyncStateManager

logger = get_logger()


class SyncStateUpdateService:
    """Handles updating and persisting sync state after operations."""

    def __init__(self, state_manager: SyncStateManager):
        """Initialize state update service.

        Args:
            state_manager: SyncStateManager for persistence
        """
        self.state_manager = state_manager

    def update_baseline_for_pulled(self, pulled_remote_ids: list[str]) -> None:
        """Update baseline state after pulling remote issues.

        Marks pulled issues as processed in the baseline state.

        Args:
            pulled_remote_ids: List of remote issue IDs that were pulled
        """
        try:
            base_state = self.state_manager.load_sync_state_from_db()
            if not base_state:
                return

            # Mark pulled issues as updated in baseline
            from datetime import datetime

            now = datetime.now(UTC)
            for remote_id in pulled_remote_ids:
                if remote_id in base_state.base_issues:
                    base_state.base_issues[remote_id].updated_at = now

            # Save updated state
            self.state_manager.save_sync_state_to_db(base_state)

        except Exception as e:
            # Log but don't raise - state update failures shouldn't break sync
            logger.error("update_sync_state_failed", error=str(e), severity="operational")
