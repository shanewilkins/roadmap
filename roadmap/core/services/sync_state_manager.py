"""Manages persistence of sync state to database and/from legacy JSON file."""

import json
from datetime import datetime
from pathlib import Path

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_state import IssueBaseState, SyncState

logger = get_logger(__name__)


class SyncStateManager:
    """Manages loading and saving sync state from/to database (with JSON fallback for migration)."""

    def __init__(self, roadmap_dir: Path, db_manager=None):
        """Initialize manager with roadmap directory and optional database.

        Args:
            roadmap_dir: Path to .roadmap directory
            db_manager: Optional DatabaseManager instance for persistent storage
        """
        self.roadmap_dir = roadmap_dir
        self.state_file = (
            roadmap_dir / ".sync-state.json"
        )  # Legacy file, kept for migration
        self.db_manager = db_manager

    def load_sync_state(self) -> SyncState | None:
        """Load sync state from file.

        Returns:
            SyncState if file exists and is valid, None otherwise
        """
        if not self.state_file.exists():
            logger.debug(
                "sync_state_file_not_found",
                path=str(self.state_file),
                reason="first_sync_or_state_cleared",
            )
            return None

        try:
            file_size = self.state_file.stat().st_size
            logger.debug(
                "sync_state_load_starting",
                path=str(self.state_file),
                file_size=file_size,
            )

            with open(self.state_file) as f:
                data = json.load(f)

            state = SyncState.from_dict(data)

            logger.info(
                "sync_state_loaded_successfully",
                issues_count=len(state.issues),
                backend=state.backend,
                last_sync=state.last_sync.isoformat() if state.last_sync else None,
                path=str(self.state_file),
            )
            return state
        except json.JSONDecodeError as e:
            logger.error(
                "sync_state_json_decode_failed",
                error=str(e),
                path=str(self.state_file),
                error_type="JSONDecodeError",
                line=e.lineno,
                column=e.colno,
            )
            return None
        except (KeyError, ValueError) as e:
            logger.error(
                "sync_state_validation_failed",
                error=str(e),
                path=str(self.state_file),
                error_type=type(e).__name__,
            )
            return None
        except OSError as e:
            logger.error(
                "sync_state_file_io_error",
                error=str(e),
                path=str(self.state_file),
                error_type="OSError",
            )
            return None
        except Exception as e:
            logger.error(
                "sync_state_load_unexpected_error",
                error=str(e),
                path=str(self.state_file),
                error_type=type(e).__name__,
            )
            return None

    def save_sync_state(self, state: SyncState) -> bool:
        """Save sync state to file.

        Args:
            state: SyncState to save

        Returns:
            True if save was successful
        """
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            logger.debug(
                "sync_state_save_starting",
                path=str(self.state_file),
                issues_count=len(state.issues),
                backend=state.backend,
            )

            with open(self.state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)

            file_size = self.state_file.stat().st_size
            logger.info(
                "sync_state_saved_successfully",
                issues_count=len(state.issues),
                backend=state.backend,
                file_size=file_size,
                path=str(self.state_file),
            )
            return True
        except OSError as e:
            logger.error(
                "sync_state_save_file_error",
                error=str(e),
                path=str(self.state_file),
                error_type="OSError",
            )
            return False
        except (TypeError, ValueError) as e:
            logger.error(
                "sync_state_serialization_error",
                error=str(e),
                error_type=type(e).__name__,
                issues_count=len(state.issues),
            )
            return False
        except Exception as e:
            logger.error(
                "sync_state_save_unexpected_error",
                error=str(e),
                path=str(self.state_file),
                error_type=type(e).__name__,
            )
            return False

    def save_sync_state_to_db(self, state: SyncState) -> bool:
        """Save sync state to database (preferred storage method).

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
                issues_count=len(state.issues),
                backend=state.backend,
            )

            # Save metadata
            conn.execute(
                "INSERT OR REPLACE INTO sync_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                ("last_sync", state.last_sync.isoformat(), datetime.utcnow()),
            )
            conn.execute(
                "INSERT OR REPLACE INTO sync_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                ("backend", state.backend, datetime.utcnow()),
            )

            # Save each issue's base state
            for issue_id, base_state in state.issues.items():
                conn.execute(
                    """INSERT OR REPLACE INTO sync_base_state
                       (issue_id, status, assignee, milestone, description, labels, synced_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        issue_id,
                        base_state.status,
                        base_state.assignee,
                        base_state.milestone,
                        base_state.description,
                        json.dumps(base_state.labels or []),
                        datetime.utcnow(),
                    ),
                )

            conn.commit()
            logger.info(
                "sync_state_saved_to_db",
                issues_count=len(state.issues),
                backend=state.backend,
            )
            return True

        except Exception as e:
            logger.error(
                "sync_state_db_save_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def load_sync_state_from_db(self) -> SyncState | None:
        """Load sync state from database.

        Returns:
            SyncState if database has valid state, None otherwise
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

            last_sync = datetime.fromisoformat(metadata["last_sync"])
            backend = metadata.get("backend", "github")

            # Get all base states
            state = SyncState(
                last_sync=last_sync,
                backend=backend,
            )

            # TODO: This DB-based approach will be replaced by git history + YAML metadata
            # For now, we skip populating issues from DB to avoid schema issues
            # See SYNC_ARCHITECTURE.md for details on new approach
            #
            # for row in conn.execute(
            #     "SELECT issue_id, status, assignee, milestone, description, labels FROM sync_base_state"
            # ):
            #     issue_id, status, assignee, milestone, description, labels_json = row
            #     base_state = IssueBaseState(
            #         id=issue_id,
            #         title="",  # Will be populated from git
            #         status=status,
            #         assignee=assignee,
            #         milestone=milestone,
            #         description=description or "",
            #         labels=json.loads(labels_json) if labels_json else [],
            #     )
            #     state.issues[issue_id] = base_state

            logger.info(
                "sync_state_loaded_from_db",
                issues_count=len(state.issues),
                backend=backend,
            )
            return state

        except Exception as e:
            logger.error(
                "sync_state_db_load_error",
                error=str(e),
                error_type=type(e).__name__,
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
            title=issue.title,  # Include title since it's synced to remote
            assignee=issue.assignee,
            milestone=issue.milestone if hasattr(issue, "milestone") else None,
            description=issue.content or "",
            labels=issue.labels or [],
            updated_at=datetime.utcnow(),
        )

    def save_base_state(self, issue: Issue, remote_version: bool = False) -> bool:
        """Update the base state for a single issue in the sync state file.

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
                issue_title=issue.title[:50],
                remote_version=remote_version,
            )

            # Load current sync state
            state = self.load_sync_state()
            if state is None:
                logger.info(
                    "creating_new_sync_state_for_issue",
                    issue_id=issue.id,
                    reason="no_existing_state",
                )
                state = SyncState(
                    last_sync=datetime.utcnow(),
                    backend="github",  # Default, will be overridden if state file exists
                )

            # Create new base state for this issue
            base_state = self.create_base_state_from_issue(issue)
            state.add_issue(issue.id, base_state)
            state.last_sync = datetime.utcnow()

            # Save the updated state
            success = self.save_sync_state(state)
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
                )
            return success
        except AttributeError as e:
            logger.error(
                "base_state_update_attribute_error",
                issue_id=issue.id if hasattr(issue, "id") else "unknown",
                error=str(e),
                error_type="AttributeError",
            )
            return False
        except Exception as e:
            logger.error(
                "base_state_update_failed",
                issue_id=issue.id if hasattr(issue, "id") else "unknown",
                error=str(e),
                error_type=type(e).__name__,
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
            backend: Backend type (default: "github")

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
                last_sync=datetime.utcnow(),
                backend=backend,
            )

            for issue in issues:
                try:
                    base_state = self.create_base_state_from_issue(issue)
                    state.add_issue(issue.id, base_state)
                except Exception as e:
                    logger.warning(
                        "skipping_issue_in_state_creation",
                        issue_id=issue.id if hasattr(issue, "id") else "unknown",
                        error=str(e),
                    )
                    continue

            logger.info(
                "sync_state_created_successfully",
                issues_count=len(issues),
                backend=backend,
                issues_in_state=len(state.issues),
            )
            return state
        except Exception as e:
            logger.error(
                "sync_state_creation_failed",
                issues_count=len(issues) if isinstance(issues, list) else "unknown",
                backend=backend,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return empty state as fallback
            return SyncState(
                last_sync=datetime.utcnow(),
                backend=backend,
            )

    def migrate_json_to_db(self) -> bool:
        """Migrate sync state from JSON file to database.

        One-time operation for existing installations to move from file-based
        to database-based sync state storage.

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
            # Load from JSON
            logger.info("sync_state_migration_starting", source="json_file")
            state = self.load_sync_state()

            if not state:
                logger.warning(
                    "sync_state_migration_load_failed",
                    reason="could_not_load_json_state",
                )
                return False

            # Save to database
            success = self.save_sync_state_to_db(state)

            if success:
                # Optionally archive the JSON file
                archive_path = self.state_file.with_suffix(".json.backup")
                try:
                    self.state_file.rename(archive_path)
                    logger.info(
                        "sync_state_migration_complete",
                        json_archived=str(archive_path),
                    )
                except OSError as e:
                    logger.warning(
                        "sync_state_migration_archive_failed",
                        error=str(e),
                        note="json_file_not_removed",
                    )
                return True
            else:
                logger.error(
                    "sync_state_migration_db_save_failed",
                    reason="could_not_save_to_database",
                )
                return False

        except Exception as e:
            logger.error(
                "sync_state_migration_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
