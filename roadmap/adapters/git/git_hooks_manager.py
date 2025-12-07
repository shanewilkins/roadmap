"""Git hook installation and management for roadmap integration."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.parser import IssueParser
from roadmap.core.domain import MilestoneStatus, Status
from roadmap.infrastructure.core import RoadmapCore

from .git import GitCommit, GitIntegration


class GitHookManager:
    """Manages Git hooks for automated roadmap integration."""

    def __init__(self, roadmap_core: RoadmapCore):
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
        if not self.hooks_dir or not self.hooks_dir.exists():
            return False

        available_hooks = ["post-commit", "pre-push", "post-merge", "post-checkout"]

        hooks_to_install = hooks or available_hooks

        try:
            for hook_name in hooks_to_install:
                if hook_name in available_hooks:
                    self._install_hook(hook_name)
            return True
        except Exception as e:
            print(f"Error installing hooks: {e}")
            return False

    def uninstall_hooks(self) -> bool:
        """Remove all roadmap Git hooks."""
        if not self.hooks_dir:
            return False

        hook_names = ["post-commit", "pre-push", "post-merge", "post-checkout"]

        try:
            for hook_name in hook_names:
                hook_file = self.hooks_dir / hook_name
                if hook_file.exists():
                    # Check if it's our hook before removing
                    content = hook_file.read_text()
                    if "roadmap-hook" in content:
                        hook_file.unlink()
            return True
        except Exception:
            return False

    def get_hooks_status(self) -> dict[str, dict[str, Any]]:
        """Get the status of all installed roadmap hooks.

        Returns:
            Dictionary with hook names as keys and status information as values.
        """
        if not self.hooks_dir or not self.hooks_dir.exists():
            return {}

        hook_names = ["post-commit", "pre-push", "post-merge", "post-checkout"]
        status = {}

        for hook_name in hook_names:
            hook_file = self.hooks_dir / hook_name
            hook_status = {
                "installed": False,
                "is_roadmap_hook": False,
                "executable": False,
                "file_exists": hook_file.exists(),
                "file_path": str(hook_file) if hook_file.exists() else None,
            }

            if hook_file.exists():
                hook_status["installed"] = True
                try:
                    content = hook_file.read_text()
                    hook_status["is_roadmap_hook"] = "roadmap-hook" in content
                    hook_status["executable"] = bool(hook_file.stat().st_mode & 0o111)
                except Exception:
                    pass

            status[hook_name] = hook_status

        return status

    def get_hook_config(self) -> dict[str, Any] | None:
        """Get the current hook configuration.

        Returns:
            Dictionary with hook configuration settings or None if not available.
        """
        config = {
            "hooks_directory": str(self.hooks_dir) if self.hooks_dir else None,
            "repository_root": str(Path.cwd()),
            "git_repository": self.git_integration.is_git_repository(),
            "available_hooks": [
                "post-commit",
                "pre-push",
                "post-merge",
                "post-checkout",
            ],
            "core_initialized": self.core is not None,
        }

        # Add status for each hook
        config["hooks_status"] = self.get_hooks_status()

        return config

    def _install_hook(self, hook_name: str):
        """Install a specific Git hook."""
        if self.hooks_dir is None:
            return False
        hook_file = self.hooks_dir / hook_name

        # Create hook script content
        hook_content = self._get_hook_content(hook_name)

        # Write hook file
        hook_file.write_text(hook_content)
        hook_file.chmod(0o755)  # Make executable

    def _get_hook_content(self, hook_name: str) -> str:
        """Get the content for a specific hook."""
        python_exec = shutil.which("python") or shutil.which("python3")

        base_script = f"""#!/bin/bash
# roadmap-hook: {hook_name}
# Auto-generated Git hook for roadmap integration

# Get the directory of this script
HOOK_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"

# Change to repository root
cd "$REPO_ROOT"

# Execute roadmap hook handler
{python_exec} -c "
import sys
sys.path.insert(0, '.')
try:
    from roadmap.adapters.git.git_hooks_manager import GitHookManager
    from roadmap.infrastructure.core import RoadmapCore
    core = RoadmapCore()
    hook_manager = GitHookManager(core)
    hook_manager.handle_{hook_name.replace('-', '_')}()
except Exception as e:
    # Silent fail to avoid breaking Git operations
    pass
"
"""
        return base_script

    def handle_post_commit(self):
        """Handle post-commit hook - log commit info.

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
            log_file = Path(".git/roadmap-hooks.log")
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp} - Commit: {latest_commit_sha[:7]}\n"

            # Append to log file if it exists
            try:
                with open(log_file, "a") as f:
                    f.write(log_entry)
            except Exception:
                pass  # Silent fail for logging

        except Exception:
            # Silent fail to avoid breaking Git operations
            pass

    def handle_post_checkout(self):
        """Handle post-checkout hook - track branch changes.

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
            log_file = Path(".git/roadmap-hooks.log")
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp} - Checkout: {branch_name}\n"

            try:
                with open(log_file, "a") as f:
                    f.write(log_entry)
            except Exception:
                pass  # Silent fail for logging

        except Exception:
            # Silent fail to avoid breaking Git operations
            pass

    def handle_pre_push(self):
        """Handle pre-push hook - basic push notification.

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
            log_file = Path(".git/roadmap-hooks.log")
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp} - Push: {current_branch}\n"

            try:
                with open(log_file, "a") as f:
                    f.write(log_entry)
            except Exception:
                pass  # Silent fail for logging

        except Exception:
            # Silent fail to avoid breaking Git operations
            pass

    def handle_post_merge(self):
        """Handle post-merge hook - update milestone progress."""
        try:
            # After a merge, check if any milestones should be updated
            self._update_milestone_progress()

        except Exception:
            pass

    def _update_issue_from_commit(
        self, issue_id: str, commit: GitCommit, progress: float | None
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

        except Exception:
            pass

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
                issue.completed_date = datetime.now().isoformat()

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

        except Exception:
            pass

    def _update_milestone_progress(self):
        """Update milestone progress based on completed issues."""
        try:
            milestones = self.core.milestones.list()

            for milestone in milestones:
                # Use string comparison for enum values to avoid typing issues
                milestone_status = (
                    str(milestone.status).lower() if milestone.status else ""
                )
                if milestone_status == "active":
                    # Get issues in this milestone
                    milestone_issues = [
                        issue
                        for issue in self.core.issues.list()
                        if issue.milestone == milestone.name
                    ]

                    if milestone_issues:
                        # Calculate progress
                        total_issues = len(milestone_issues)
                        completed_issues = len(
                            [i for i in milestone_issues if i.status == Status.CLOSED]
                        )
                        progress = (completed_issues / total_issues) * 100

                        # Update milestone progress (use setattr for type safety)
                        if hasattr(milestone, "calculated_progress"):
                            milestone.calculated_progress = progress

                        # Auto-complete milestone if all issues are done
                        if (
                            progress >= 100
                            and milestone.status != MilestoneStatus.CLOSED
                        ):
                            # Use MilestoneStatus enum for type safety
                            milestone.status = MilestoneStatus.CLOSED
                            if hasattr(milestone, "actual_end_date"):
                                milestone.actual_end_date = datetime.now()

                        # Use getattr to safely call save_milestone method
                        save_method = getattr(self.core, "save_milestone", None)
                        if save_method and callable(save_method):
                            save_method(milestone)

        except Exception:
            pass

    def _set_branch_context(self, branch_name: str, issue_id: str):
        """Set branch context for CLI commands."""
        try:
            context_file = Path(".roadmap_branch_context.json")
            context = {
                "branch": branch_name,
                "issue_id": issue_id,
                "timestamp": datetime.now().isoformat(),
            }
            context_file.write_text(json.dumps(context, indent=2))

        except Exception:
            pass
