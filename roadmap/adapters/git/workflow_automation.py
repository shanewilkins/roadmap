"""High-level workflow automation for Git integration."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.adapters.persistence.parser import IssueParser
from roadmap.core.domain import Issue, Status
from roadmap.infrastructure.coordination.core import RoadmapCore

from .git import GitCommit, GitIntegration
from .git_hooks_manager import GitHookManager

logger = get_logger()


class WorkflowAutomation:
    """High-level workflow automation orchestrator."""

    def __init__(self, roadmap_core: RoadmapCore):
        """Initialize WorkflowAutomation.

        Args:
            roadmap_core: Core roadmap integration instance.
        """
        self.core = roadmap_core
        self.hook_manager = GitHookManager(roadmap_core)
        self.git_integration = GitIntegration()

    def setup_automation(self, features: list[str] | None = None) -> dict[str, bool]:
        """Set up automated workflow features.

        Args:
            features: List of features to enable. Options:
                     ['git-hooks', 'status-automation', 'progress-tracking']

        Returns:
            Dict mapping feature names to success status.
        """
        all_features = ["git-hooks", "status-automation", "progress-tracking"]
        features_to_enable = features or all_features

        results = {}

        if "git-hooks" in features_to_enable:
            results["git-hooks"] = self.hook_manager.install_hooks()

        if "status-automation" in features_to_enable:
            results["status-automation"] = self._setup_status_automation()

        if "progress-tracking" in features_to_enable:
            results["progress-tracking"] = self._setup_progress_tracking()

        return results

    def disable_automation(self) -> bool:
        """Disable all workflow automation."""
        try:
            # Remove Git hooks
            self.hook_manager.uninstall_hooks()

            # Clean up context files
            context_files = [
                ".roadmap_branch_context.json",
                ".roadmap_automation_config.json",
                ".roadmap_progress_tracking.json",
            ]

            for file_path in context_files:
                if Path(file_path).exists():
                    Path(file_path).unlink()

            return True

        except Exception as e:
            logger.error("context_cleanup_failed", error=str(e))
            return False

    def _setup_status_automation(self) -> bool:
        """Set up intelligent status automation rules."""
        try:
            # Create automation config
            config = {
                "status_rules": {
                    "auto_in_progress": True,  # Move to in-progress on first commit
                    "auto_done_on_close": True,  # Mark done on "closes" commit
                    "auto_blocked_detection": True,  # Detect blocked status from patterns
                },
                "progress_rules": {
                    "commit_based_progress": True,  # Update progress from commits
                    "milestone_auto_complete": True,  # Auto-complete milestones
                    "velocity_tracking": True,  # Track team velocity
                },
            }

            config_file = Path(".roadmap_automation_config.json")
            config_file.write_text(json.dumps(config, indent=2))
            return True

        except Exception as e:
            logger.error("status_automation_setup_failed", error=str(e))
            return False

    def _setup_progress_tracking(self) -> bool:
        """Set up automated progress tracking."""
        try:
            # Initialize progress tracking state
            tracking_state = {
                "enabled": True,
                "last_sync": datetime.now(UTC).isoformat(),
                "tracked_metrics": [
                    "commit_frequency",
                    "issue_completion_rate",
                    "milestone_progress",
                    "team_velocity",
                ],
            }

            tracking_file = Path(".roadmap_progress_tracking.json")
            tracking_file.write_text(json.dumps(tracking_state, indent=2))
            return True

        except Exception as e:
            logger.error("progress_tracking_setup_failed", error=str(e))
            return False

    def sync_all_issues_with_git(self) -> dict[str, Any]:
        """Sync all issues with their Git activity."""
        results = {"synced_issues": 0, "updated_issues": [], "errors": []}

        try:
            issues = self.core.issues.list()
            commits = self.git_integration.get_recent_commits(count=100)

            # Build commit lookup by issue references
            issue_commits = {}
            for commit in commits:
                references = commit.extract_roadmap_references()
                for issue_id in references:
                    if issue_id not in issue_commits:
                        issue_commits[issue_id] = []
                    issue_commits[issue_id].append(commit)

            # Update issues based on their Git activity
            for issue in issues:
                if issue.id in issue_commits:
                    try:
                        updated = self._sync_issue_with_commits(
                            issue, issue_commits[issue.id]
                        )
                        if updated:
                            results["synced_issues"] += 1
                            results["updated_issues"].append(
                                {
                                    "id": issue.id,
                                    "title": issue.title,
                                    "commits": len(issue_commits[issue.id]),
                                }
                            )
                    except Exception as e:
                        results["errors"].append(f"Issue {issue.id}: {str(e)}")

        except Exception as e:
            results["errors"].append(f"Sync error: {str(e)}")

        return results

    def _sync_issue_with_commits(self, issue: Issue, commits: list[GitCommit]) -> bool:
        """Sync a single issue with its Git commits."""
        updated = False

        # Sort commits by date
        commits.sort(key=lambda c: c.date)

        # Initialize git_commits if not present
        if not hasattr(issue, "git_commits"):
            issue.git_commits = []

        # Process commits and extract progress information
        highest_progress, is_completed = self._process_commits_for_issue(issue, commits)

        # Update issue status and progress based on extracted data
        updated = self._update_issue_status_and_progress(
            issue, highest_progress, is_completed
        )

        if updated:
            issue_path = self.core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

        return updated

    def _process_commits_for_issue(
        self, issue: Issue, commits: list[GitCommit]
    ) -> tuple[float | None, bool]:
        """Process commits for an issue and extract progress and completion status.

        Returns:
            Tuple of (highest_progress_percentage, is_completed_bool)
        """
        highest_progress: float | None = None
        is_completed = False

        for commit in commits:
            # Check if commit already tracked
            if any(ref.get("hash") == commit.hash for ref in issue.git_commits):
                continue

            # Extract progress from commit
            progress = commit.extract_progress_info()
            if progress is not None:
                if highest_progress is None or progress > highest_progress:
                    highest_progress = progress

            # Check for completion keywords in commit message
            if self._is_completion_commit(commit):
                is_completed = True

            # Build and add commit reference
            self._add_commit_reference_to_issue(
                issue, commit, progress, is_completed, commits
            )

        return highest_progress, is_completed

    def _is_completion_commit(self, commit: GitCommit) -> bool:
        """Check if commit contains completion keywords."""
        completion_keywords = ["closes roadmap:", "fixes roadmap:"]
        return any(keyword in commit.message.lower() for keyword in completion_keywords)

    def _add_commit_reference_to_issue(
        self,
        issue: Issue,
        commit: GitCommit,
        progress: float | None,
        is_completed: bool,
        commits: list[GitCommit],
    ):
        """Add a commit reference to the issue's git_commits list."""
        commit_ref = {
            "hash": commit.hash,
            "message": commit.message,
            "date": commit.date.isoformat(),
            "progress": progress,
            "completion": is_completed and commit == commits[-1],
        }
        issue.git_commits.append(commit_ref)

    def _update_issue_status_and_progress(
        self, issue: Issue, highest_progress: float | None, is_completed: bool
    ) -> bool:
        """Update issue status and progress based on extracted data.

        Returns:
            True if issue was updated, False otherwise.
        """
        updated = False

        # Update progress percentage
        if highest_progress is not None:
            issue.progress_percentage = highest_progress
            updated = True
        elif is_completed:
            # If completed without explicit progress, set to 100%
            issue.progress_percentage = 100.0
            updated = True

        # Update status based on completion and progress
        if is_completed and issue.status != Status.CLOSED:
            issue.status = Status.CLOSED
            issue.completed_date = datetime.now(UTC).isoformat()
            updated = True
        elif highest_progress and highest_progress > 0 and issue.status == Status.TODO:
            issue.status = Status.IN_PROGRESS
            updated = True

        return updated
