"""GitSyncMonitor - Detect and sync file changes to database cache."""

from pathlib import Path
from typing import Any

from roadmap.adapters.git.git_command_executor import GitCommandExecutor
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class GitSyncMonitor:
    """Detects file changes via git diff and syncs them to database cache.

    This class enables cheap change detection:
    - Uses `git diff --name-only` for millisecond change detection
    - Tracks last synced commit to avoid redundant work
    - Filters changes to only .roadmap/issues/ files
    - Syncs only changed files to database (vs filesystem scan)

    Typical usage:
        monitor = GitSyncMonitor(repo_path, state_manager)
        changes = monitor.detect_changes()
        if changes:
            monitor.sync_to_database(changes)

    This enables:
    - `roadmap list`: git diff (50ms) + DB query (5ms) = 55ms total
    - Instead of: filesystem scan (1000ms) + parse (500ms) = 1500ms total
    """

    # Metadata file to track last synced commit
    SYNC_METADATA_FILE = "sync_git_state.txt"

    def __init__(self, repo_path: Path | None = None, state_manager: Any | None = None):
        """Initialize GitSyncMonitor.

        Args:
            repo_path: Path to git repository root
            state_manager: StateManager for database operations (optional for Phase 1)
        """
        self.repo_path = repo_path or Path.cwd()
        self.state_manager = state_manager
        self.git_executor = GitCommandExecutor(self.repo_path)

        # Cache last known commit to avoid re-checking
        self._cached_last_synced_commit: str | None = None
        self._cached_current_commit: str | None = None

    def detect_changes(self) -> dict[str, str]:
        """Detect changes since last sync.

        Uses `git diff --name-only` for fast change detection.

        Returns:
            Dictionary mapping file paths to change types:
            - "modified": File exists and changed
            - "added": New file
            - "deleted": File was removed
            - Empty dict if no changes detected

        Example:
            {
                ".roadmap/issues/issue-123.yaml": "modified",
                ".roadmap/issues/issue-456.yaml": "added",
                ".roadmap/issues/issue-789.yaml": "deleted",
            }
        """
        try:
            # Check if we're in a git repo
            if not self.git_executor.is_git_repository():
                logger.debug("Not in a git repository, skipping git sync")
                return {}

            # Get current commit
            current_commit = self._get_current_commit()
            if not current_commit:
                logger.debug("Unable to get current commit")
                return {}

            # Get last synced commit
            last_synced = self._get_last_synced_commit()
            if last_synced == current_commit:
                logger.debug(
                    "Already synced to current commit",
                    current=current_commit[:8],
                )
                return {}

            # Get changed files
            changes = self._get_changed_files(last_synced)
            logger.debug(
                "Detected file changes",
                current=current_commit[:8],
                previous=last_synced[:8] if last_synced else "none",
                change_count=len(changes),
            )

            return changes

        except Exception as e:
            logger.error(
                "Error detecting changes",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}

    def sync_to_database(self, changes: dict[str, str]) -> bool:
        """Sync detected changes to database cache.

        Args:
            changes: Dictionary of changes from detect_changes()

        Returns:
            True if sync successful, False otherwise
        """
        if not changes:
            logger.debug("No changes to sync")
            return True

        if not self.state_manager:
            logger.warning("State manager not configured, skipping database sync")
            return False

        try:
            logger.debug("Syncing changes to database", change_count=len(changes))

            # Phase 1: Just track the sync state
            # Phase 2: Will actually sync files to database
            self._save_last_synced_commit()

            logger.debug("Sync to database complete")
            return True

        except Exception as e:
            logger.error(
                "Error syncing to database",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def _get_changed_files(self, base_commit: str | None = None) -> dict[str, str]:
        """Get list of changed files since base commit.

        Args:
            base_commit: Commit SHA to compare against. If None, uses initial commit.

        Returns:
            Dictionary mapping file paths to change types
        """
        changes: dict[str, str] = {}

        try:
            # If no base commit (first sync), get all issues files
            if not base_commit:
                return self._get_all_issues_files()

            # Get changed files between base and current
            changed_files = self.git_executor.run(
                ["diff", "--name-status", base_commit, "HEAD"]
            )

            if not changed_files:
                return {}

            # Parse git diff output
            # Format: M\tpath/to/file (Modified)
            #         A\tpath/to/file (Added)
            #         D\tpath/to/file (Deleted)
            for line in changed_files.split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue

                status, path = parts
                path = path.strip()

                # Only track .roadmap/issues/ changes
                if not self._is_issues_file(path):
                    continue

                # Map git status to our status
                status_map = {"M": "modified", "A": "added", "D": "deleted"}
                changes[path] = status_map.get(status, "modified")

            return changes

        except Exception as e:
            logger.error(
                "Error getting changed files",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}

    def _get_all_issues_files(self) -> dict[str, str]:
        """Get all issues files for initial sync.

        Returns:
            Dictionary mapping all issue files to "added" status
        """
        all_files: dict[str, str] = {}

        try:
            # Use git ls-files to get all tracked files
            git_files = self.git_executor.run(["ls-files"])
            if not git_files:
                return {}

            for path in git_files.split("\n"):
                path = path.strip()
                if self._is_issues_file(path):
                    all_files[path] = "added"

            logger.debug(
                "Found all issues files for initial sync",
                file_count=len(all_files),
            )

            return all_files

        except Exception as e:
            logger.error(
                "Error getting all issues files",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}

    def _is_issues_file(self, path: str) -> bool:
        """Check if path is a .roadmap/issues/ file.

        Args:
            path: File path to check

        Returns:
            True if file is in .roadmap/issues/ or .roadmap/archive/issues/
        """
        return ".roadmap/issues/" in path or ".roadmap/archive/issues/" in path

    def _get_current_commit(self) -> str | None:
        """Get the current HEAD commit SHA.

        Returns:
            Commit SHA, or None if not in a valid git state
        """
        if self._cached_current_commit:
            return self._cached_current_commit

        try:
            commit = self.git_executor.run(["rev-parse", "HEAD"])
            self._cached_current_commit = commit
            return commit
        except Exception as e:
            logger.error(
                "Error getting current commit",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _get_last_synced_commit(self) -> str | None:
        """Get the last commit we synced to database.

        Returns:
            Commit SHA, or None if never synced
        """
        if self._cached_last_synced_commit is not None:
            return self._cached_last_synced_commit

        try:
            # In Phase 1, read from metadata file
            # In Phase 2, will read from database sync_base_state
            metadata_path = self.repo_path / self.SYNC_METADATA_FILE

            if metadata_path.exists():
                commit = metadata_path.read_text().strip()
                self._cached_last_synced_commit = commit
                return commit

            # No previous sync
            self._cached_last_synced_commit = None
            return None

        except Exception as e:
            logger.error(
                "Error getting last synced commit",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _save_last_synced_commit(self) -> bool:
        """Save current commit as the last synced commit.

        Returns:
            True if save successful
        """
        try:
            current_commit = self._get_current_commit()
            if not current_commit:
                logger.error("Cannot save last synced commit: no current commit")
                return False

            # In Phase 1, write to metadata file
            # In Phase 2, will write to database sync_base_state
            metadata_path = self.repo_path / self.SYNC_METADATA_FILE

            metadata_path.write_text(f"{current_commit}\n")

            # Update cache
            self._cached_last_synced_commit = current_commit

            logger.debug(
                "Saved last synced commit",
                commit=current_commit[:8],
            )

            return True

        except Exception as e:
            logger.error(
                "Error saving last synced commit",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def clear_cache(self) -> None:
        """Clear internal commit caches.

        Useful for testing or forcing a fresh check.
        """
        self._cached_last_synced_commit = None
        self._cached_current_commit = None
