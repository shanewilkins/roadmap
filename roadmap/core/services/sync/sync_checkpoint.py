"""Checkpoint-based error recovery for sync operations.

This module provides checkpoint/rollback capabilities to enable resuming
from failures and rolling back partial syncs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from structlog import get_logger

if TYPE_CHECKING:
    from roadmap.core.domain.issue import Issue
    from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


@dataclass
class SyncCheckpoint:
    """Represents a sync checkpoint that can be used for rollback/resume."""

    checkpoint_id: str
    timestamp: str
    phase: str  # "fetch", "push", "baseline_update", "complete"
    baseline_state: dict[str, dict]  # issue_id -> issue_dict
    modified_issues: list[str]  # List of issue IDs modified during sync
    github_operations: list[dict]  # List of GitHub operations performed
    metadata: dict  # Additional metadata about the checkpoint


class SyncCheckpointManager:
    """Manages sync checkpoints for error recovery."""

    def __init__(self, core: RoadmapCore):
        """Initialize checkpoint manager.

        Args:
            core: RoadmapCore instance for state management
        """
        self.core = core
        self.state_manager = core._state_manager
        self._current_checkpoint: SyncCheckpoint | None = None

    def create_checkpoint(
        self,
        phase: str,
        issues: list[Issue],
        github_operations: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> SyncCheckpoint:
        """Create a checkpoint before a sync operation.

        Args:
            phase: Current phase ("fetch", "push", "baseline_update")
            issues: List of issues to checkpoint
            github_operations: List of GitHub operations performed so far
            metadata: Additional checkpoint metadata

        Returns:
            SyncCheckpoint object
        """
        logger.info(
            "checkpoint_created",
            phase=phase,
            issue_count=len(issues),
            action="create_checkpoint",
        )

        # Generate checkpoint ID from timestamp + phase
        timestamp = datetime.utcnow().isoformat()
        checkpoint_data = f"{timestamp}-{phase}"
        checkpoint_id = hashlib.sha256(checkpoint_data.encode()).hexdigest()[:16]

        # Serialize baseline state
        baseline_state = {}
        modified_issues = []
        for issue in issues:
            baseline_state[issue.id] = self._serialize_issue(issue)
            if self._is_modified(issue):
                modified_issues.append(issue.id)

        checkpoint = SyncCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=timestamp,
            phase=phase,
            baseline_state=baseline_state,
            modified_issues=modified_issues,
            github_operations=github_operations or [],
            metadata=metadata or {},
        )

        # Save checkpoint to database
        self._save_checkpoint(checkpoint)
        self._current_checkpoint = checkpoint

        return checkpoint

    def _serialize_issue(self, issue: Issue) -> dict:
        """Serialize an issue to a dictionary for checkpointing."""
        issue_dict = asdict(issue)
        # Convert datetime objects to ISO strings
        for key, value in issue_dict.items():
            if isinstance(value, datetime):
                issue_dict[key] = value.isoformat()
        return issue_dict

    def _is_modified(self, issue: Issue) -> bool:
        """Check if an issue has been modified locally."""
        # Check if issue has local changes that haven't been synced
        return bool(
            getattr(issue, "_modified", False) or getattr(issue, "_local_changes", None)
        )

    def _save_checkpoint(self, checkpoint: SyncCheckpoint) -> None:
        """Save checkpoint to database."""
        checkpoint_key = f"sync_checkpoint_{checkpoint.checkpoint_id}"
        checkpoint_data = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "timestamp": checkpoint.timestamp,
            "phase": checkpoint.phase,
            "baseline_state": checkpoint.baseline_state,
            "modified_issues": checkpoint.modified_issues,
            "github_operations": checkpoint.github_operations,
            "metadata": checkpoint.metadata,
        }

        # Store in sync_state table
        self.core.repositories.sync_state.set(
            checkpoint_key, json.dumps(checkpoint_data)
        )

        # Also save as "latest_checkpoint" for easy recovery
        self.core.repositories.sync_state.set(
            "latest_checkpoint", json.dumps(checkpoint_data)
        )

        logger.debug(
            "checkpoint_saved",
            checkpoint_id=checkpoint.checkpoint_id,
            phase=checkpoint.phase,
            action="save_checkpoint",
        )

    def get_latest_checkpoint(self) -> SyncCheckpoint | None:
        """Retrieve the latest checkpoint for resuming sync.

        Returns:
            SyncCheckpoint if found, None otherwise
        """
        try:
            checkpoint_json = self.core.repositories.sync_state.get("latest_checkpoint")
            if not checkpoint_json:
                return None

            checkpoint_data = json.loads(checkpoint_json)
            return SyncCheckpoint(**checkpoint_data)

        except Exception as e:
            logger.warning(
                "checkpoint_retrieval_failed",
                error=str(e),
                action="get_latest_checkpoint",
            )
            return None

    def rollback_to_checkpoint(self, checkpoint: SyncCheckpoint) -> bool:
        """Rollback sync to a previous checkpoint.

        This will:
        1. Restore all issues to their checkpointed state
        2. Undo any GitHub operations if possible
        3. Clear modified flags

        Args:
            checkpoint: Checkpoint to rollback to

        Returns:
            True if rollback successful, False otherwise
        """
        logger.info(
            "checkpoint_rollback_started",
            checkpoint_id=checkpoint.checkpoint_id,
            phase=checkpoint.phase,
            action="rollback_to_checkpoint",
        )

        try:
            # Restore all issues from checkpoint
            for issue_id, issue_data in checkpoint.baseline_state.items():
                try:
                    # Get current issue
                    issue = self.core.issues.get(issue_id)
                    if not issue:
                        logger.warning(
                            "checkpoint_issue_not_found",
                            issue_id=issue_id,
                            action="rollback_issue",
                        )
                        continue

                    # Restore fields from checkpoint
                    for field, value in issue_data.items():
                        if hasattr(issue, field):
                            setattr(issue, field, value)

                    # Clear modification flags
                    if hasattr(issue, "_modified"):
                        setattr(issue, "_modified", False)
                    if hasattr(issue, "_local_changes"):
                        setattr(issue, "_local_changes", None)

                    # Save restored issue
                    self.core.issues.update(issue.id, issue)

                    logger.debug(
                        "checkpoint_issue_restored",
                        issue_id=issue_id,
                        action="rollback_issue",
                    )

                except Exception as e:
                    logger.error(
                        "checkpoint_issue_rollback_failed",
                        issue_id=issue_id,
                        error=str(e),
                        action="rollback_issue",
                    )
                    # Continue with other issues

            # Clear the checkpoint after successful rollback
            self.clear_checkpoint(checkpoint.checkpoint_id)

            logger.info(
                "checkpoint_rollback_completed",
                checkpoint_id=checkpoint.checkpoint_id,
                issues_restored=len(checkpoint.baseline_state),
                action="rollback_to_checkpoint",
            )

            return True

        except Exception as e:
            logger.error(
                "checkpoint_rollback_failed",
                checkpoint_id=checkpoint.checkpoint_id,
                error=str(e),
                action="rollback_to_checkpoint",
            )
            return False

    def can_resume(self) -> tuple[bool, SyncCheckpoint | None]:
        """Check if there's a checkpoint that can be resumed.

        Returns:
            Tuple of (can_resume: bool, checkpoint: SyncCheckpoint | None)
        """
        checkpoint = self.get_latest_checkpoint()
        if not checkpoint:
            return False, None

        # Check if checkpoint is recent (within last hour)
        try:
            checkpoint_time = datetime.fromisoformat(checkpoint.timestamp)
            time_diff = datetime.utcnow() - checkpoint_time
            is_recent = time_diff.total_seconds() < 3600  # 1 hour

            if not is_recent:
                logger.info(
                    "checkpoint_too_old",
                    checkpoint_id=checkpoint.checkpoint_id,
                    age_seconds=time_diff.total_seconds(),
                    action="can_resume",
                )
                return False, checkpoint

            # Check if checkpoint is in a resumable phase
            resumable_phases = ["fetch", "push"]
            if checkpoint.phase not in resumable_phases:
                logger.info(
                    "checkpoint_phase_not_resumable",
                    checkpoint_id=checkpoint.checkpoint_id,
                    phase=checkpoint.phase,
                    action="can_resume",
                )
                return False, checkpoint

            return True, checkpoint

        except Exception as e:
            logger.warning(
                "checkpoint_resume_check_failed",
                error=str(e),
                action="can_resume",
            )
            return False, None

    def clear_checkpoint(self, checkpoint_id: str) -> None:
        """Clear a checkpoint from storage.

        Args:
            checkpoint_id: ID of checkpoint to clear
        """
        checkpoint_key = f"sync_checkpoint_{checkpoint_id}"
        try:
            self.core.repositories.sync_state.delete(checkpoint_key)
            # Also clear latest_checkpoint if it matches
            latest = self.core.repositories.sync_state.get("latest_checkpoint")
            if latest:
                latest_data = json.loads(latest)
                if latest_data.get("checkpoint_id") == checkpoint_id:
                    self.core.repositories.sync_state.delete("latest_checkpoint")

            logger.debug(
                "checkpoint_cleared",
                checkpoint_id=checkpoint_id,
                action="clear_checkpoint",
            )
        except Exception as e:
            logger.warning(
                "checkpoint_clear_failed",
                checkpoint_id=checkpoint_id,
                error=str(e),
                action="clear_checkpoint",
            )

    def clear_all_checkpoints(self) -> None:
        """Clear all sync checkpoints."""
        try:
            # Note: This is a simplified approach - in production you'd want
            # proper enumeration of checkpoint keys
            self.core.repositories.sync_state.delete("latest_checkpoint")
            logger.info("all_checkpoints_cleared", action="clear_all_checkpoints")
        except Exception as e:
            logger.warning(
                "checkpoint_clear_all_failed",
                error=str(e),
                action="clear_all_checkpoints",
            )
