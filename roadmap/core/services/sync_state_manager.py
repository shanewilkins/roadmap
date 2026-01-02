"""Manages persistence of sync state to/from .sync-state.json file."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from structlog import get_logger

from roadmap.core.models.sync_state import IssueBaseState, SyncState
from roadmap.core.domain.issue import Issue

logger = get_logger(__name__)


class SyncStateManager:
    """Manages loading and saving sync state from/to .sync-state.json."""

    def __init__(self, roadmap_dir: Path):
        """Initialize manager with roadmap directory.

        Args:
            roadmap_dir: Path to .roadmap directory
        """
        self.roadmap_dir = roadmap_dir
        self.state_file = roadmap_dir / ".sync-state.json"

    def load_sync_state(self) -> Optional[SyncState]:
        """Load sync state from file.

        Returns:
            SyncState if file exists and is valid, None otherwise
        """
        if not self.state_file.exists():
            logger.debug("sync_state_file_not_found", path=str(self.state_file))
            return None

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            state = SyncState.from_dict(data)
            logger.debug(
                "sync_state_loaded",
                issues_count=len(state.issues),
                backend=state.backend,
            )
            return state
        except Exception as e:
            logger.warning(
                "sync_state_load_failed",
                error=str(e),
                path=str(self.state_file),
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
            with open(self.state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.debug(
                "sync_state_saved",
                issues_count=len(state.issues),
                backend=state.backend,
            )
            return True
        except Exception as e:
            logger.error(
                "sync_state_save_failed",
                error=str(e),
                path=str(self.state_file),
            )
            return False

    def create_base_state_from_issue(self, issue: Issue) -> IssueBaseState:
        """Create a base state snapshot from an Issue object.

        Args:
            issue: Issue object to snapshot

        Returns:
            IssueBaseState representing the current state of the issue
        """
        return IssueBaseState(
            id=issue.id,
            status=str(issue.status) if issue.status else "unknown",
            assignee=issue.assignee,
            milestone=issue.milestone if hasattr(issue, "milestone") else None,
            description=issue.content or "",
            labels=issue.labels or [],
            updated_at=datetime.utcnow(),
        )

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
        state = SyncState(
            last_sync=datetime.utcnow(),
            backend=backend,
        )

        for issue in issues:
            base_state = self.create_base_state_from_issue(issue)
            state.add_issue(issue.id, base_state)

        logger.debug(
            "sync_state_created",
            issues_count=len(issues),
            backend=backend,
        )
        return state
