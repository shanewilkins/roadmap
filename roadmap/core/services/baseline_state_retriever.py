"""Baseline state retrieval using git history and YAML metadata.

This module replaces the previous DB-based baseline approach with:
1. Local baseline: Retrieved from git history at last_synced timestamp
2. Remote baseline: Stored in sync_metadata YAML frontmatter

This enables idempotent syncs without complex database state management.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.adapters.persistence.git_history import (
    FileNotFound,
    GitHistoryError,
    get_file_at_timestamp,
)
from roadmap.adapters.persistence.parser.issue import IssueParser
from roadmap.core.models.sync_state import IssueBaseState

logger = get_logger(__name__)


class BaselineRetrievalError(Exception):
    """Raised when baseline retrieval fails."""

    pass


class BaselineStateRetriever:
    """Retrieves baseline state from git history and YAML metadata."""

    def __init__(self, issues_dir: Path):
        """Initialize with issues directory.

        Args:
            issues_dir: Path to issues directory
        """
        self.issues_dir = issues_dir

    def get_baseline_from_file(self, issue_file: Path) -> IssueBaseState | None:
        """Get baseline state directly from current issue file.

        Used for initial baseline creation on first sync, where we extract
        the current state directly without looking in git history.

        Args:
            issue_file: Path to issue file

        Returns:
            IssueBaseState extracted from file, or None if extraction fails
        """
        try:
            if not issue_file.exists():
                logger.debug(
                    "baseline_file_not_found",
                    issue_file=str(issue_file),
                )
                return None

            content = issue_file.read_text(encoding="utf-8")
            return self._extract_baseline_from_content(content, issue_file)
        except Exception as e:
            logger.warning(
                "baseline_from_file_extraction_error",
                issue_file=str(issue_file),
                error=str(e),
            )
            return None

    def get_local_baseline(
        self, issue_file: Path, last_synced: datetime
    ) -> IssueBaseState | None:
        """Get local baseline state from git history.

        Retrieves the issue file as it existed at the last_synced timestamp,
        then extracts the relevant fields to create a baseline.

        Args:
            issue_file: Path to issue file
            last_synced: Timestamp of last successful sync

        Returns:
            IssueBaseState if found, None if file didn't exist at that time
        """
        try:
            # Get file content as it existed at last_synced time
            file_content = get_file_at_timestamp(str(issue_file), last_synced)

            if not file_content:
                logger.debug(
                    "local_baseline_file_not_found",
                    issue_file=str(issue_file),
                    last_synced=last_synced.isoformat(),
                )
                return None

            # Parse the file to extract baseline fields
            baseline = self._extract_baseline_from_content(file_content, issue_file)

            logger.debug(
                "local_baseline_retrieved",
                issue_file=str(issue_file),
                status=baseline.status if baseline else None,
            )
            return baseline

        except FileNotFound:
            logger.debug(
                "local_baseline_file_not_in_history",
                issue_file=str(issue_file),
                last_synced=last_synced.isoformat(),
                reason="file_did_not_exist_at_timestamp",
            )
            return None
        except GitHistoryError as e:
            logger.warning(
                "local_baseline_git_error",
                issue_file=str(issue_file),
                error=str(e),
            )
            raise BaselineRetrievalError(
                f"Failed to retrieve baseline from git: {e}"
            ) from e
        except Exception as e:
            logger.warning(
                "local_baseline_extraction_error",
                issue_file=str(issue_file),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def get_remote_baseline(self, issue_file: Path) -> IssueBaseState | None:
        """Get remote baseline from sync_metadata in issue file.

        The sync_metadata YAML frontmatter contains a remote_state snapshot
        that represents the last-synced state from the remote backend.

        Args:
            issue_file: Path to issue file

        Returns:
            IssueBaseState extracted from remote_state, or None if not present
        """
        try:
            sync_metadata = IssueParser.load_sync_metadata(issue_file)

            if not sync_metadata:
                logger.debug(
                    "remote_baseline_not_found",
                    issue_file=str(issue_file),
                    reason="no_sync_metadata",
                )
                return None

            remote_state = sync_metadata.get("remote_state")
            if not remote_state:
                logger.debug(
                    "remote_baseline_not_found",
                    issue_file=str(issue_file),
                    reason="no_remote_state_in_metadata",
                )
                return None

            baseline = self._extract_baseline_from_remote_state(
                remote_state, issue_file
            )

            logger.debug(
                "remote_baseline_retrieved",
                issue_file=str(issue_file),
                status=baseline.status if baseline else None,
            )
            return baseline

        except Exception as e:
            logger.warning(
                "remote_baseline_extraction_error",
                issue_file=str(issue_file),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _extract_baseline_from_content(
        self, content: str, issue_file: Path
    ) -> IssueBaseState | None:
        """Extract baseline fields from issue file content.

        Args:
            content: File content (with YAML frontmatter)
            issue_file: Path to issue file (for logging)

        Returns:
            IssueBaseState or None if extraction fails
        """
        from roadmap.adapters.persistence.parser.frontmatter import FrontmatterParser
        from roadmap.common.datetime_parser import parse_datetime

        try:
            frontmatter, _ = FrontmatterParser.parse_content(content)

            # Parse updated datetime
            updated_at = datetime.now(timezone.utc)
            if frontmatter.get("updated"):
                updated_value = frontmatter["updated"]
                if isinstance(updated_value, datetime):
                    updated_at = updated_value
                else:
                    parsed = parse_datetime(str(updated_value), "file")
                    if parsed:
                        updated_at = parsed

            return IssueBaseState(
                id=frontmatter.get("id", ""),
                title=frontmatter.get("title", ""),
                status=frontmatter.get("status", "todo"),
                assignee=frontmatter.get("assignee"),
                milestone=frontmatter.get("milestone"),
                headline=frontmatter.get("headline", ""),
                labels=frontmatter.get("labels", []),
                updated_at=updated_at,
            )
        except Exception as e:
            logger.debug(
                "baseline_extraction_failed",
                issue_file=str(issue_file),
                error=str(e),
            )
            return None

    def _extract_baseline_from_remote_state(
        self, remote_state: dict[str, Any], issue_file: Path
    ) -> IssueBaseState | None:
        """Extract baseline from remote_state snapshot in sync_metadata.

        Args:
            remote_state: Remote state dict from sync_metadata
            issue_file: Path to issue file (for logging)

        Returns:
            IssueBaseState or None if extraction fails
        """
        try:
            # Parse datetime if present
            updated_at = datetime.now(timezone.utc)
            if "updated_at" in remote_state:
                if isinstance(remote_state["updated_at"], str):
                    updated_at = datetime.fromisoformat(remote_state["updated_at"])
                else:
                    updated_at = remote_state["updated_at"]

            return IssueBaseState(
                id=remote_state.get("id", ""),
                title=remote_state.get("title", ""),
                status=remote_state.get("status", "open"),
                assignee=remote_state.get("assignee"),
                milestone=remote_state.get("milestone"),
                headline=remote_state.get("headline", ""),
                labels=remote_state.get("labels", []),
                updated_at=updated_at,
            )
        except Exception as e:
            logger.debug(
                "remote_baseline_extraction_failed",
                issue_file=str(issue_file),
                error=str(e),
            )
            return None
