"""Handles baseline state loading and updates for sync operations.

Extracted from SyncMergeEngine to separate baseline management concerns.
"""

from datetime import UTC, datetime
from typing import Any

from structlog import get_logger

from roadmap.core.models.sync_state import IssueBaseState, SyncState

logger = get_logger(__name__)


class BaselineStateHandler:
    """Manages baseline state loading and updates."""

    def __init__(self, core: Any, state_update_service: Any):
        """Initialize with core services.

        Args:
            core: RoadmapCore instance with database access
            state_update_service: SyncStateUpdateService for baseline updates
        """
        self.core = core
        self.state_update_service = state_update_service

    def load_baseline_state(self) -> SyncState | None:
        """Load baseline state from database.

        Returns:
            SyncState object if baseline exists, None otherwise
        """
        try:
            db_baseline = self.core.db.get_sync_baseline()
            if db_baseline:
                logger.debug(
                    "baseline_loaded_from_database", issue_count=len(db_baseline)
                )
                issues = {}
                for issue_id, data in db_baseline.items():
                    issues[issue_id] = IssueBaseState(
                        id=issue_id,
                        status=data.get("status", "todo"),
                        title="",
                        assignee=data.get("assignee"),
                        milestone=data.get("milestone"),
                        headline=data.get("headline", ""),
                        content=data.get("content", ""),
                        labels=data.get("labels", []),
                    )

                sync_state = SyncState(
                    last_sync=datetime.now(UTC),
                    backend="github",
                    issues=issues,
                )
                return sync_state

            logger.debug("baseline_not_found_in_database")
            return None

        except Exception as e:
            logger.warning(
                "baseline_load_failed", error=str(e), error_type=type(e).__name__
            )
            return None

    def update_baseline_for_pulled(self, pulled_remote_ids: list[str]) -> None:
        """Update baseline after pulling changes.

        Args:
            pulled_remote_ids: List of remote issue IDs that were pulled
        """
        self.state_update_service.update_baseline_for_pulled(pulled_remote_ids)
