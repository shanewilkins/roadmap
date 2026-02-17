"""Manages persistence of sync state for three-way merge operations.

The new SyncState model tracks three snapshots:
- base_issues: The agreed-upon state from last successful sync
- local_issues: Current local state (populated before sync)
- remote_issues: Current remote state (fetched during sync)

This manager persists the base_issues snapshot and sync metadata.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState

logger = get_logger(__name__)


class SyncStateManager:
    """Manages loading and saving sync state from git-based baselines."""

    def __init__(self, roadmap_dir: Path, db_manager=None):
        """Initialize manager with roadmap directory.

        Args:
            roadmap_dir: Path to .roadmap directory
            db_manager: Optional DatabaseManager instance for persistent storage
        """
        self.roadmap_dir = roadmap_dir
        self.db_manager = db_manager
        self.state_file = roadmap_dir / "sync_state.json"

    def load_sync_state(self) -> SyncState | None:
        """Load sync state from git-based baseline metadata.

        Returns:
            SyncState if baseline metadata exists and is valid, None otherwise
        """
        # Git-based baselines are retrieved via SyncRetrievalOrchestrator
        # This method is kept for compatibility but delegates to git history
        logger.debug(
            "sync_state_load_deprecated",
            reason="Use SyncRetrievalOrchestrator.get_baseline_state() instead",
        )
        return None

    def save_sync_state(self, state: SyncState) -> bool:
        """Save sync state to git-based baseline metadata.

        Args:
            state: SyncState to save

        Returns:
            True if save was successful
        """
        # Git-based baselines are managed via SyncRetrievalOrchestrator
        # This method is deprecated in favor of git history + YAML metadata
        logger.debug(
            "sync_state_save_deprecated",
            reason="Use SyncRetrievalOrchestrator baseline management instead",
        )
        return True

    def save_sync_state_to_db(self, state: SyncState) -> bool:
        """Save sync state to database (preferred storage method).

        Persists the base_issues snapshot and last_sync_time metadata.

        Args:
            state: SyncState to save

        Returns:
            True if save was successful
        """
        if not self.db_manager:
            logger.debug(
                "sync_state_db_save_skipped",
                reason="no_database_manager",
            )
            return False

        try:
            import json

            conn = self.db_manager._get_connection()

            logger.debug(
                "sync_state_db_save_starting",
                base_issues_count=len(state.base_issues),
                sync_time=state.last_sync_time,
            )

            # Save metadata - only last_sync_time (no backend in new model)
            if state.last_sync_time:
                conn.execute(
                    "INSERT OR REPLACE INTO sync_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                    (
                        "last_sync",
                        state.last_sync_time.isoformat(),
                        datetime.now(UTC).isoformat(),
                    ),
                )

            # Save each base issue state
            for issue_id, base_state in state.base_issues.items():
                conn.execute(
                    """INSERT OR REPLACE INTO sync_base_state
                       (issue_id, status, assignee, title, description, labels, synced_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        issue_id,
                        base_state.status,
                        base_state.assignee,
                        base_state.title,
                        base_state.description,
                        json.dumps(base_state.labels or []),
                        datetime.now(UTC).isoformat(),
                    ),
                )

            conn.commit()
            logger.info(
                "sync_state_saved_to_db",
                base_issues_count=len(state.base_issues),
            )
            return True

        except Exception as e:
            logger.error(
                "sync_state_db_save_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            return False

    def load_sync_state_from_db(self) -> SyncState | None:
        """Load sync state from database.

        Returns:
            SyncState with base_issues if database has valid state, None otherwise
        """
        if not self.db_manager:
            logger.debug(
                "sync_state_db_load_skipped",
                reason="no_database_manager",
            )
            return None

        try:
            conn = self.db_manager._get_connection()

            # Get metadata
            metadata = {}
            for row in conn.execute("SELECT key, value FROM sync_metadata"):
                metadata[row[0]] = row[1]

            if not metadata.get("last_sync"):
                logger.debug(
                    "sync_state_db_empty",
                    reason="no_last_sync_metadata",
                )
                return None

            last_sync_time = datetime.fromisoformat(metadata["last_sync"])

            # Create new SyncState with metadata
            state = SyncState(
                last_sync_time=last_sync_time,
            )

            # Load base states from database
            try:
                for row in conn.execute(
                    "SELECT issue_id, status, assignee, title, description, labels FROM sync_base_state"
                ):
                    issue_id, status, assignee, title, description, labels_json = row
                    base_state = IssueBaseState(
                        id=issue_id,
                        status=status,
                        title=title or "",
                        assignee=assignee,
                        description=description or "",
                        labels=json.loads(labels_json) if labels_json else [],
                    )
                    state.base_issues[issue_id] = base_state
            except Exception as e:
                logger.warning(
                    "sync_state_db_load_issues_failed",
                    error=str(e),
                    note="metadata_loaded_but_issues_skipped",
                )

            logger.info(
                "sync_state_loaded_from_db",
                base_issues_count=len(state.base_issues),
            )
            return state

        except Exception as e:
            logger.error(
                "sync_state_db_load_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            return None

    def create_base_state_from_issue(self, issue: Issue) -> IssueBaseState:
        """Create a base state snapshot from an Issue object.

        Args:
            issue: Issue object to snapshot

        Returns:
            IssueBaseState representing the current state of the issue
        """
        # Extract status value properly - handle enum types
        status_value = issue.status
        if hasattr(status_value, "value"):
            # It's an enum, use the value
            status_value = status_value.value
        elif status_value is None:
            status_value = "unknown"
        else:
            status_value = str(status_value)

        return IssueBaseState(
            id=issue.id,
            status=status_value,
            title=issue.title,
            assignee=issue.assignee,
            description=issue.content or "",
            labels=issue.labels or [],
            updated_at=datetime.now(UTC),
        )

    def save_base_state(self, issue: Issue, remote_version: bool = False) -> bool:
        """Update the base state for a single issue after successful sync.

        This method is called after successfully syncing an issue to update
        the persisted state so it won't be re-synced next time.

        Args:
            issue: Issue object that was synced
            remote_version: If True, marks this as the remote version (post-push)

        Returns:
            True if update was successful
        """
        try:
            logger.debug(
                "base_state_update_starting",
                issue_id=issue.id,
                issue_title=issue.title[:50] if issue.title else "",
                remote_version=remote_version,
            )

            # Load current sync state or create new one
            state = self.load_sync_state_from_db()
            if state is None:
                logger.info(
                    "creating_new_sync_state_for_issue",
                    issue_id=issue.id,
                    reason="no_existing_state",
                )
                state = SyncState(
                    last_sync_time=datetime.now(UTC),
                )

            # Create new base state for this issue
            base_state = self.create_base_state_from_issue(issue)
            state.base_issues[issue.id] = base_state
            state.last_sync_time = datetime.now(UTC)

            # Save the updated state to database
            success = self.save_sync_state_to_db(state)
            if success:
                logger.info(
                    "base_state_updated_successfully",
                    issue_id=issue.id,
                    remote_version=remote_version,
                    status=base_state.status,
                )
            else:
                logger.warning(
                    "base_state_update_save_failed",
                    issue_id=issue.id,
                    severity="operational",
                )
            return success
        except AttributeError as e:
            logger.error(
                "base_state_update_attribute_error",
                issue_id=issue.id if hasattr(issue, "id") else "unknown",
                error=str(e),
                error_type="AttributeError",
                severity="system_error",
            )
            return False
        except Exception as e:
            logger.error(
                "base_state_update_failed",
                issue_id=issue.id if hasattr(issue, "id") else "unknown",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            return False

    def create_sync_state_from_issues(
        self,
        issues: list[Issue],
        backend: str = "github",
    ) -> SyncState:
        """Create a complete sync state from a list of issues.

        Args:
            issues: List of Issue objects
            backend: Backend type (used for logging only, not stored in new model)

        Returns:
            SyncState with base states for all issues
        """
        try:
            logger.debug(
                "creating_sync_state_from_issues",
                issues_count=len(issues),
                backend=backend,
            )

            state = SyncState(
                last_sync_time=datetime.now(UTC),
            )

            for issue in issues:
                try:
                    base_state = self.create_base_state_from_issue(issue)
                    state.base_issues[issue.id] = base_state
                except Exception as e:
                    logger.warning(
                        "skipping_issue_in_state_creation",
                        issue_id=issue.id if hasattr(issue, "id") else "unknown",
                        error=str(e),
                        severity="operational",
                    )
                    continue

            logger.info(
                "sync_state_created_successfully",
                issues_count=len(issues),
                backend=backend,
                issues_in_state=len(state.base_issues),
            )
            return state
        except Exception as e:
            logger.error(
                "sync_state_creation_failed",
                issues_count=len(issues) if isinstance(issues, list) else "unknown",
                backend=backend,
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            # Return empty state as fallback
            return SyncState(
                last_sync_time=datetime.now(UTC),
            )

    def migrate_json_to_db(self) -> bool:
        """Migrate sync state from JSON file to database (legacy operation).

        One-time operation for existing installations to move from file-based
        to database-based sync state storage. With the new model, this operation
        should not be needed as state is created fresh from issues.

        Returns:
            True if migration was successful or not needed
        """
        if not self.db_manager:
            logger.debug(
                "sync_state_migration_skipped",
                reason="no_database_manager",
            )
            return False

        # Check if JSON file exists
        if not self.state_file.exists():
            logger.debug(
                "sync_state_migration_not_needed",
                reason="no_legacy_json_file",
            )
            return True

        try:
            logger.info("sync_state_migration_starting", source="json_file")
            logger.warning(
                "sync_state_migration_deprecated",
                note="new_model_creates_fresh_state_from_issues",
            )

            # Archive the JSON file
            try:
                archive_path = self.state_file.with_suffix(".json.backup")
                self.state_file.rename(archive_path)
                logger.info(
                    "sync_state_legacy_json_archived",
                    archived_to=str(archive_path),
                )
                return True
            except OSError as e:
                logger.warning(
                    "sync_state_migration_archive_failed",
                    error=str(e),
                    note="json_file_remains",
                    severity="operational",
                )
                return False

        except Exception as e:
            logger.error(
                "sync_state_migration_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            return False
