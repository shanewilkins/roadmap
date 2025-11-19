"""Git hooks and workflow automation for roadmap integration."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..application.core import RoadmapCore
from .git import GitCommit, GitIntegration
from ..domain import Issue, Status, MilestoneStatus
from ..parser import IssueParser


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
    from roadmap.git_hooks import GitHookManager
    from roadmap.core import RoadmapCore
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
            issue = self.core.get_issue(issue_id)
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
            issue = self.core.get_issue(issue_id)
            if not issue:
                return

            # Mark as done if not already
            if issue.status != Status.DONE:
                issue.status = Status.DONE
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
            milestones = self.core.list_milestones()

            for milestone in milestones:
                # Use string comparison for enum values to avoid typing issues
                milestone_status = (
                    str(milestone.status).lower() if milestone.status else ""
                )
                if milestone_status == "active":
                    # Get issues in this milestone
                    milestone_issues = [
                        issue
                        for issue in self.core.list_issues()
                        if (
                            hasattr(issue, "milestone_id")
                            and hasattr(milestone, "id")
                            and issue.milestone_id == milestone.id
                        )
                    ]

                    if milestone_issues:
                        # Calculate progress
                        total_issues = len(milestone_issues)
                        completed_issues = len(
                            [i for i in milestone_issues if i.status == Status.DONE]
                        )
                        progress = (completed_issues / total_issues) * 100

                        # Update milestone progress (use setattr for type safety)
                        if hasattr(milestone, "progress"):
                            milestone.progress = progress

                        # Auto-complete milestone if all issues are done
                        if progress >= 100 and milestone.status != MilestoneStatus.CLOSED:
                            # Use MilestoneStatus enum for type safety
                            if hasattr(milestone, "status"):
                                milestone.status = MilestoneStatus.CLOSED
                            if hasattr(milestone, "completed_date"):
                                milestone.completed_date = datetime.now().isoformat()

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


class WorkflowAutomation:
    """High-level workflow automation orchestrator."""

    def __init__(self, roadmap_core: RoadmapCore):
        self.core = roadmap_core
        self.hook_manager = GitHookManager(roadmap_core)
        self.git_integration = GitIntegration()

    def setup_automation(self, features: list[str] | None = None) -> dict[str, bool]:
        """Setup automated workflow features.

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

        except Exception:
            return False

    def _setup_status_automation(self) -> bool:
        """Setup intelligent status automation rules."""
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

        except Exception:
            return False

    def _setup_progress_tracking(self) -> bool:
        """Setup automated progress tracking."""
        try:
            # Initialize progress tracking state
            tracking_state = {
                "enabled": True,
                "last_sync": datetime.now().isoformat(),
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

        except Exception:
            return False

    def sync_all_issues_with_git(self) -> dict[str, Any]:
        """Sync all issues with their Git activity."""
        results = {"synced_issues": 0, "updated_issues": [], "errors": []}

        try:
            issues = self.core.list_issues()
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

        # Track latest progress and completion status
        highest_progress = None
        is_completed = False

        for commit in commits:
            # Check if commit already tracked
            if any(ref.get("hash") == commit.hash for ref in issue.git_commits):
                continue

            # Extract progress
            progress = commit.extract_progress_info()
            if progress is not None:
                if highest_progress is None or progress > highest_progress:
                    highest_progress = progress

            # Check for completion keywords
            if any(
                keyword in commit.message.lower()
                for keyword in ["closes roadmap:", "fixes roadmap:"]
            ):
                is_completed = True
                # Don't overwrite progress - completion means 100% but preserve highest explicit progress

            # Add commit reference
            commit_ref = {
                "hash": commit.hash,
                "message": commit.message,
                "date": commit.date.isoformat(),
                "progress": progress,
                "completion": is_completed
                and commit == commits[-1],  # Only mark last commit as completion
            }

            issue.git_commits.append(commit_ref)
            updated = True

        # Update issue status and progress
        if highest_progress is not None:
            issue.progress_percentage = highest_progress
            updated = True
        elif is_completed:
            # If completed without explicit progress, set to 100%
            issue.progress_percentage = 100.0
            updated = True

        if is_completed and issue.status != Status.DONE:
            issue.status = Status.DONE
            issue.completed_date = datetime.now().isoformat()
            updated = True
        elif highest_progress and highest_progress > 0 and issue.status == Status.TODO:
            issue.status = Status.IN_PROGRESS
            updated = True

        if updated:
            issue_path = self.core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

        return updated
