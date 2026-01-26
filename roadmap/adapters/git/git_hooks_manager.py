"""Git hook installation and management for roadmap integration."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.adapters.persistence.parser import IssueParser
from roadmap.core.domain import MilestoneStatus, Status
from roadmap.infrastructure.coordination.core import RoadmapCore

from .git import GitCommit, GitIntegration
from .hook_installer import HookInstaller
from .hook_registry import HookRegistry, HookStatus

logger = get_logger()


class GitHookManager:
    """Manages Git hooks for automated roadmap integration."""

    def __init__(self, roadmap_core: RoadmapCore):
        """Initialize GitHookManager.

        Args:
            roadmap_core: Core roadmap integration instance.
        """
        self.core = roadmap_core
        self.git_integration = GitIntegration()
        self.hooks_dir = (
            Path(".git/hooks") if self.git_integration.is_git_repository() else None
        )

    def install_hooks(self, hooks: list[str] | None = None) -> bool:
        """Install roadmap Git hooks.

        Args:
            hooks: List of hook names to install. If None, installs all available hooks.

        Returns:
            True if hooks were installed successfully.
        """
        installer = HookInstaller(self.hooks_dir)
        return installer.install(hooks)

    def uninstall_hooks(self, hooks: list[str] | None = None) -> bool:
        """Remove roadmap Git hooks.

        Args:
            hooks: List of hook names to uninstall. If None, uninstalls all.

        Returns:
            True if hooks were uninstalled successfully.
        """
        installer = HookInstaller(self.hooks_dir)
        return installer.uninstall(hooks)

    def get_hooks_status(self) -> dict[str, dict[str, Any]]:
        """Get the status of all installed roadmap hooks.

        Returns:
            Dictionary with hook names as keys and status information as values.
        """
        if not self.hooks_dir or not self.hooks_dir.exists():
            return {}

        status = {}
        for hook_name in HookRegistry.get_available_hooks():
            hook_file = self.hooks_dir / hook_name
            status[hook_name] = HookStatus.get_status_dict(hook_name, hook_file)

        return status

    def get_hook_config(self) -> dict[str, Any]:
        """Get the current hook configuration.

        Returns:
            Dictionary with hook configuration settings.
        """
        return {
            "hooks_directory": str(self.hooks_dir) if self.hooks_dir else None,
            "repository_root": str(Path.cwd()),
            "git_repository": self.git_integration.is_git_repository(),
            "available_hooks": HookRegistry.get_available_hooks(),
            "core_initialized": self.core is not None,
            "hooks_status": self.get_hooks_status(),
        }

    def handle_post_commit(self):
        """Handle post-commit hook - log commit info and trigger auto-sync.

        Note: CI tracking (post-1.0 feature) has been moved to future/ci_tracking.py
        """
        try:
            # Get the latest commit SHA for logging
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            latest_commit_sha = result.stdout.strip()

            if not latest_commit_sha:
                return

            # Log the commit for basic tracking
            self._log_hook_activity("Commit", latest_commit_sha[:7])

            # Trigger auto-sync if enabled
            self._trigger_auto_sync_on_commit(latest_commit_sha)

        except Exception as e:
            # Silent fail to avoid breaking Git operations
            logger.error(
                "handle_post_commit_failed", error=str(e), severity="operational"
            )

    def handle_post_checkout(self):
        """Handle post-checkout hook - track branch changes and trigger auto-sync.

        Note: Advanced CI branch tracking (post-1.0 feature) has been moved to future/ci_tracking.py
        """
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch_name = result.stdout.strip()

            if not branch_name:
                return

            # Log the branch checkout for basic tracking
            self._log_hook_activity("Checkout", branch_name)

            # Trigger auto-sync if enabled
            self._trigger_auto_sync_on_checkout(branch_name)

        except Exception as e:
            # Silent fail to avoid breaking Git operations
            logger.error(
                "handle_post_checkout_failed", error=str(e), severity="operational"
            )

    def handle_pre_push(self):
        """Handle pre-push hook - basic push notification and trigger auto-sync.

        Note: Advanced CI automation (post-1.0 feature) has been moved to future/ci_tracking.py
        """
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()

            if not current_branch:
                return

            # Log the push for basic tracking
            self._log_hook_activity("Push", current_branch)

            # Note: We don't auto-sync on pre-push to avoid blocking the push
            # Users can manually sync before pushing if desired

        except Exception as e:
            # Silent fail to avoid breaking Git operations
            logger.error("handle_pre_push_failed", error=str(e), severity="operational")

    def handle_post_merge(self):
        """Handle post-merge hook - update milestone progress and trigger auto-sync."""
        try:
            # After a merge, check if any milestones should be updated
            self._update_milestone_progress()

            # Trigger auto-sync if enabled
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                merge_commit_sha = result.stdout.strip()
                self._trigger_auto_sync_on_merge(merge_commit_sha)
            except Exception as e:
                logger.debug("trigger_auto_sync_on_merge_failed", error=str(e))

        except Exception as e:
            logger.error(
                "handle_post_merge_failed", error=str(e), severity="operational"
            )

    def _log_hook_activity(self, activity_type: str, activity_detail: str) -> None:
        """Log hook activity to .git/roadmap-hooks.log.

        Args:
            activity_type: Type of activity (Commit, Checkout, Push, etc)
            activity_detail: Details of the activity
        """
        try:
            log_file = Path(".git/roadmap-hooks.log")
            timestamp = datetime.now(UTC).isoformat()
            log_entry = f"{timestamp} - {activity_type}: {activity_detail}\n"

            with open(log_file, "a") as f:
                f.write(log_entry)
        except Exception as e:
            logger.debug(
                "log_hook_activity_failed", error=str(e)
            )  # Silent fail for logging

    def _update_issue_from_commit(
        self, issue_id: str, commit: GitCommit, progress: float | None = None
    ):
        """Update an issue based on commit information."""
        try:
            issue = self.core.issues.get(issue_id)
            if not issue:
                return

            # Update progress if specified
            if progress is not None:
                issue.progress_percentage = min(100.0, max(0.0, progress))

            # Update status based on commit activity
            if issue.status == Status.TODO and progress and progress > 0:
                issue.status = Status.IN_PROGRESS

            # Add commit reference to issue history
            if not hasattr(issue, "git_commits"):
                issue.git_commits = []

            commit_ref = {
                "hash": commit.hash,
                "message": commit.message,
                "date": commit.date.isoformat(),
                "progress": progress,
            }

            # Avoid duplicates
            if not any(ref["hash"] == commit.hash for ref in issue.git_commits):
                issue.git_commits.append(commit_ref)

            # Save updated issue
            issue_path = self.core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

        except Exception as e:
            logger.error(
                "update_issue_from_commit_failed", error=str(e), severity="operational"
            )

    def _complete_issue_from_commit(self, issue_id: str, commit: GitCommit):
        """Mark an issue as completed based on commit message."""
        try:
            issue = self.core.issues.get(issue_id)
            if not issue:
                return

            # Mark as closed if not already
            if issue.status != Status.CLOSED:
                issue.status = Status.CLOSED
                issue.progress_percentage = 100.0
                issue.completed_date = datetime.now(UTC).isoformat()

                # Add completion commit reference
                if not hasattr(issue, "git_commits"):
                    issue.git_commits = []

                completion_ref = {
                    "hash": commit.hash,
                    "message": commit.message,
                    "date": commit.date.isoformat(),
                    "completion": True,
                }

                issue.git_commits.append(completion_ref)
                issue_path = self.core.issues_dir / issue.filename
                IssueParser.save_issue_file(issue, issue_path)

        except Exception as e:
            logger.error(
                "complete_issue_from_commit_failed",
                error=str(e),
                severity="operational",
            )

    def _is_milestone_active(self, milestone) -> bool:
        """Check if milestone is active.

        Args:
            milestone: Milestone object to check

        Returns:
            True if milestone status is active
        """
        milestone_status = str(milestone.status).lower() if milestone.status else ""
        return milestone_status == "active"

    def _get_milestone_issues(self, milestone) -> list:
        """Get all issues in a milestone.

        Args:
            milestone: Milestone object

        Returns:
            List of issues in the milestone
        """
        return [
            issue
            for issue in self.core.issues.list()
            if issue.milestone == milestone.name
        ]

    def _calculate_milestone_progress(self, milestone_issues: list) -> float:
        """Calculate progress percentage for milestone.

        Args:
            milestone_issues: List of issues in the milestone

        Returns:
            Progress percentage (0-100)
        """
        if not milestone_issues:
            return 0.0

        total_issues = len(milestone_issues)
        completed_issues = len(
            [i for i in milestone_issues if i.status == Status.CLOSED]
        )
        return (completed_issues / total_issues) * 100

    def _update_milestone_attributes(self, milestone, progress: float) -> None:
        """Update milestone attributes based on progress.

        Args:
            milestone: Milestone object to update
            progress: Progress percentage
        """
        # Update calculated progress
        if hasattr(milestone, "calculated_progress"):
            milestone.calculated_progress = progress

        # Auto-complete if 100% done
        if progress >= 100 and milestone.status != MilestoneStatus.CLOSED:
            milestone.status = MilestoneStatus.CLOSED
            if hasattr(milestone, "actual_end_date"):
                milestone.actual_end_date = datetime.now(UTC)

    def _save_milestone(self, milestone) -> None:
        """Save updated milestone to storage.

        Args:
            milestone: Milestone object to save
        """
        save_method = getattr(self.core, "save_milestone", None)
        if save_method and callable(save_method):
            save_method(milestone)

    def _update_milestone_progress(self):
        """Update milestone progress based on completed issues."""
        try:
            milestones = self.core.milestones.list()

            for milestone in milestones:
                if self._is_milestone_active(milestone):
                    milestone_issues = self._get_milestone_issues(milestone)

                    if milestone_issues:
                        progress = self._calculate_milestone_progress(milestone_issues)
                        self._update_milestone_attributes(milestone, progress)
                        self._save_milestone(milestone)

        except Exception as e:
            logger.error(
                "update_milestone_progress_failed", error=str(e), severity="operational"
            )

    def _trigger_auto_sync_on_commit(self, commit_sha: str | None = None):
        """Trigger auto-sync after commit if enabled.

        Args:
            commit_sha: Git commit SHA for logging
        """
        self._trigger_auto_sync_operation(
            "auto_sync_on_commit",
            commit_sha=commit_sha,
            confirm=False,  # Non-interactive in hooks
        )

    def _trigger_auto_sync_on_checkout(self, branch: str | None = None):
        """Trigger auto-sync after checkout if enabled.

        Args:
            branch: Branch name for logging
        """
        self._trigger_auto_sync_operation(
            "auto_sync_on_checkout",
            branch=branch,
            confirm=False,  # Non-interactive in hooks
        )

    def _trigger_auto_sync_on_merge(self, commit_sha: str | None = None):
        """Trigger auto-sync after merge if enabled.

        Args:
            commit_sha: Merge commit SHA for logging
        """
        self._trigger_auto_sync_operation(
            "auto_sync_on_merge",
            commit_sha=commit_sha,
            confirm=False,  # Non-interactive in hooks
        )

    def _trigger_auto_sync_operation(self, operation: str, **kwargs) -> None:
        """Execute an auto-sync operation with common error handling.

        Args:
            operation: The name of the auto-sync method to call
            **kwargs: Arguments to pass to the sync method
        """
        try:
            from roadmap.core.services.git.git_hook_auto_sync_service import (
                GitHookAutoSyncService,
            )

            # Load config
            config_path = Path(".roadmap") / "config.json"
            if not config_path.exists():
                return

            # Initialize service and load config
            service = GitHookAutoSyncService(self.core)
            if not service.load_config_from_file(config_path):
                return

            # Trigger sync if enabled (no confirmation in hooks)
            method = getattr(service, operation, None)
            if method:
                method(**kwargs)

        except Exception as e:
            # Silent fail to avoid breaking Git operations
            logger.error("trigger_auto_sync_operation_failed", error=str(e))
