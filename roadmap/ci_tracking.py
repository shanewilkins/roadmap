"""
CI/CD Integration for automatic issue branch and commit tracking.

This module provides functionality to automatically track git branches and commits
associated with specific issues, enabling better traceability from work items to
actual code changes and deployments.
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .core import RoadmapCore
from .git_integration import GitIntegration
from .models import Status
from .parser import IssueParser

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """Represents a git commit with metadata."""

    sha: str
    message: str
    author: str
    date: datetime
    branch: str | None = None


@dataclass
class GitBranch:
    """Represents a git branch with metadata."""

    name: str
    created_date: datetime | None = None
    last_commit_sha: str | None = None
    is_active: bool = True


@dataclass
class CITrackingConfig:
    """Configuration for CI/CD tracking behavior."""

    # Branch tracking patterns
    branch_patterns: list[str] = field(
        default_factory=lambda: [
            r"feature/({issue_id})-.*",
            r"bugfix/({issue_id})-.*",
            r"hotfix/({issue_id})-.*",
            r"({issue_id})-.*",
            r".*/({issue_id})/.*",
            r"\b({issue_id})\b",  # Any issue ID as a word boundary (for multi-ID branches)
        ]
    )

    # Commit message patterns
    commit_patterns: list[str] = field(
        default_factory=lambda: [
            r"(?:fixes?|closes?|resolves?)\s+#?({issue_id})",
            r"({issue_id})[:]\s",
            r"(?:related to|refs?)\s+({issue_id})",
            r"closes\s+({issue_id}):",
            r"\((?:fixes?|closes?)\s+#?({issue_id})\)",
            r"\b({issue_id})\b",  # Any issue ID as a word boundary
        ]
    )

    # Automation behavior
    auto_start_on_branch: bool = True
    auto_close_on_merge: bool = True
    auto_progress_on_pr: bool = True

    # Repository configuration
    main_branches: list[str] = field(
        default_factory=lambda: ["main", "master", "develop"]
    )
    track_all_commits: bool = False
    scan_commit_history: bool = True


class CITracker:
    """Core CI/CD tracking engine for automatic issue association."""

    def __init__(
        self, roadmap_core: RoadmapCore, config: CITrackingConfig | None = None
    ):
        """Initialize CI/CD tracker.

        Args:
            roadmap_core: Core roadmap functionality
            config: CI tracking configuration
        """
        self.roadmap_core = roadmap_core
        self.config = config or CITrackingConfig()
        self.git = GitIntegration()
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, list[re.Pattern]]:
        """Compile regex patterns for better performance."""
        compiled = {"branch": [], "commit": []}

        # Replace {issue_id} placeholder with actual regex for 8-char hex IDs
        issue_id_pattern = r"[a-fA-F0-9]{8}"

        for pattern in self.config.branch_patterns:
            regex_pattern = pattern.replace("{issue_id}", issue_id_pattern)
            compiled["branch"].append(re.compile(regex_pattern, re.IGNORECASE))

        for pattern in self.config.commit_patterns:
            regex_pattern = pattern.replace("{issue_id}", issue_id_pattern)
            compiled["commit"].append(re.compile(regex_pattern, re.IGNORECASE))

        return compiled

    def extract_issue_ids_from_branch(self, branch_name: str) -> list[str]:
        """Extract issue IDs from a branch name.

        Args:
            branch_name: Name of the git branch

        Returns:
            List of issue IDs found in the branch name
        """
        issue_ids = []

        for pattern in self._compiled_patterns["branch"]:
            for match in pattern.finditer(branch_name):
                # Extract the first group (issue ID)
                if match.groups():
                    issue_id = match.group(1).lower()
                    if len(issue_id) == 8 and issue_id not in issue_ids:
                        issue_ids.append(issue_id)

        return issue_ids

    def extract_issue_ids_from_commit(self, commit_message: str) -> list[str]:
        """Extract issue IDs from a commit message.

        Args:
            commit_message: Git commit message

        Returns:
            List of issue IDs found in the commit message
        """
        issue_ids = []

        for pattern in self._compiled_patterns["commit"]:
            for match in pattern.finditer(commit_message):
                if match.groups():
                    issue_id = match.group(1).lower()
                    if len(issue_id) == 8 and issue_id not in issue_ids:
                        issue_ids.append(issue_id)

        return issue_ids

    def parse_progress_marker(self, commit_message: str) -> int | None:
        """Extract progress percentage from commit message.

        Looks for patterns like [progress:75%] or (progress:50%)

        Args:
            commit_message: Git commit message

        Returns:
            Progress percentage (0-100) or None if not found
        """
        patterns = [
            r"\[progress:\s*(\d+)%?\]",
            r"\(progress:\s*(\d+)%?\)",
            r"progress:\s*(\d+)%",
            r"(\d+)%\s*complete",
            r"(\d+)%\s*done",
        ]

        for pattern in patterns:
            match = re.search(pattern, commit_message, re.IGNORECASE)
            if match:
                progress = int(match.group(1))
                # Clamp to valid range
                return max(0, min(100, progress))

        return None

    def parse_completion_marker(self, commit_message: str, issue_id: str) -> bool:
        """Check if commit message indicates issue completion.

        Looks for patterns like:
        - [closes roadmap:id] or (closes roadmap:id)
        - fixes #id or closes #id
        - complete feature [roadmap:id]

        Args:
            commit_message: Git commit message
            issue_id: Specific issue ID to check for

        Returns:
            True if this commit indicates the issue is complete
        """
        patterns = [
            rf"\[closes?\s+(?:roadmap:)?{issue_id}\]",
            rf"\(closes?\s+(?:roadmap:)?{issue_id}\)",
            rf"closes?\s+(?:roadmap:)?{issue_id}",
            rf"fixes?\s+#?{issue_id}",
            rf"resolves?\s+#?{issue_id}",
            rf"complete.*{issue_id}",
            rf"{issue_id}.*complete",
            rf"finished?\s+{issue_id}",
            rf"{issue_id}.*(?:done|finished)",
        ]

        for pattern in patterns:
            if re.search(pattern, commit_message, re.IGNORECASE):
                return True

        return False

    def get_current_branch(self) -> str | None:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def get_all_branches(self) -> list[GitBranch]:
        """Get all git branches with metadata."""
        try:
            # Get all branches
            result = subprocess.run(
                ["git", "branch", "-a", "--format=%(refname:short)"],
                capture_output=True,
                text=True,
                check=True,
            )

            branches = []
            for line in result.stdout.strip().split("\n"):
                if line and not line.startswith("origin/"):
                    branch_name = line.strip()

                    # Get last commit for this branch
                    try:
                        commit_result = subprocess.run(
                            ["git", "log", "-1", "--format=%H", branch_name],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        last_commit = commit_result.stdout.strip()
                    except subprocess.CalledProcessError:
                        last_commit = None

                    branches.append(
                        GitBranch(
                            name=branch_name,
                            last_commit_sha=last_commit,
                            is_active=True,
                        )
                    )

            return branches
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not retrieve git branches")
            return []

    def get_commits_for_branch(
        self, branch_name: str, limit: int = 100
    ) -> list[GitCommit]:
        """Get recent commits for a specific branch.

        Args:
            branch_name: Name of the git branch
            limit: Maximum number of commits to retrieve

        Returns:
            List of GitCommit objects
        """
        try:
            # Get commit history for branch
            result = subprocess.run(
                [
                    "git",
                    "log",
                    branch_name,
                    f"--max-count={limit}",
                    "--format=%H|%an|%ai|%s",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 3)
                    if len(parts) >= 4:
                        sha, author, date_str, message = parts
                        try:
                            date = parser.parse_github_datetime(date_str)
                        except ValueError:
                            date = datetime.now()

                        commits.append(
                            GitCommit(
                                sha=sha,
                                message=message,
                                author=author,
                                date=date,
                                branch=branch_name,
                            )
                        )

            return commits
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(f"Could not retrieve commits for branch {branch_name}")
            return []

    def add_branch_to_issue(self, issue_id: str, branch_name: str) -> bool:
        """Associate a git branch with an issue.

        Args:
            issue_id: Issue identifier
            branch_name: Name of the git branch

        Returns:
            True if association was successful
        """
        try:
            issue = self.roadmap_core.get_issue(issue_id)
            if not issue:
                logger.warning(f"Issue {issue_id} not found")
                return False

            # Add branch if not already present
            if branch_name not in issue.git_branches:
                issue.git_branches.append(branch_name)
                issue.updated = datetime.now()

                # Save using the same pattern as RoadmapCore.update_issue
                issue_path = self.roadmap_core.issues_dir / issue.filename
                IssueParser.save_issue_file(issue, issue_path)

                logger.info(f"Added branch {branch_name} to issue {issue_id}")
                return True

            return True  # Already associated
        except Exception as e:
            logger.error(f"Failed to add branch {branch_name} to issue {issue_id}: {e}")
            return False

    def add_commit_to_issue(
        self, issue_id: str, commit_sha: str, commit_message: str | None = None
    ) -> bool:
        """Associate a git commit with an issue.

        Args:
            issue_id: Issue identifier
            commit_sha: Git commit SHA
            commit_message: Optional commit message for logging

        Returns:
            True if association was successful
        """
        try:
            issue = self.roadmap_core.get_issue(issue_id)
            if not issue:
                logger.warning(f"Issue {issue_id} not found")
                return False

            # Add commit if not already present
            # Check if commit already exists by SHA
            existing_shas = [
                commit.get("sha", commit) if isinstance(commit, dict) else commit
                for commit in issue.git_commits
            ]

            if commit_sha not in existing_shas:
                # Create commit object
                commit_obj = {
                    "sha": commit_sha,
                    "message": commit_message or "Unknown",
                    "date": datetime.now().isoformat(),
                }
                issue.git_commits.append(commit_obj)
                issue.updated = datetime.now()

                # Save using the same pattern as RoadmapCore.update_issue
                issue_path = self.roadmap_core.issues_dir / issue.filename
                IssueParser.save_issue_file(issue, issue_path)

                logger.info(f"Added commit {commit_sha[:8]} to issue {issue_id}")
                return True

            return True  # Already associated
        except Exception as e:
            logger.error(f"Failed to add commit {commit_sha} to issue {issue_id}: {e}")
            return False

    def remove_branch_from_issue(self, issue_id: str, branch_name: str) -> bool:
        """Remove branch association from an issue.

        Args:
            issue_id: Issue identifier
            branch_name: Name of the git branch

        Returns:
            True if removal was successful
        """
        try:
            issue = self.roadmap_core.get_issue(issue_id)
            if not issue:
                return False

            if branch_name in issue.git_branches:
                issue.git_branches.remove(branch_name)
                issue.updated = datetime.now()

                # Save using the same pattern as RoadmapCore.update_issue
                issue_path = self.roadmap_core.issues_dir / issue.filename
                IssueParser.save_issue_file(issue, issue_path)

                logger.info(f"Removed branch {branch_name} from issue {issue_id}")
                return True

            return True  # Already not associated
        except Exception as e:
            logger.error(
                f"Failed to remove branch {branch_name} from issue {issue_id}: {e}"
            )
            return False

    def update_issue_progress(self, issue_id: str, progress_percent: int) -> bool:
        """Update the progress percentage of an issue.

        Args:
            issue_id: Issue identifier
            progress_percent: Progress percentage (0-100)

        Returns:
            True if progress was updated, False otherwise
        """
        try:
            issue = self.roadmap_core.get_issue(issue_id)
            if not issue:
                logger.warning(f"Issue {issue_id} not found for progress update")
                return False

            # Update progress
            old_progress = issue.progress_percentage or 0
            issue.progress_percentage = progress_percent
            issue.updated = datetime.now()

            # Auto-update status based on progress
            if progress_percent > 0 and issue.status == Status.TODO:
                issue.status = Status.IN_PROGRESS

            # Save the issue
            issue_path = self.roadmap_core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

            logger.info(
                f"Updated issue {issue_id} progress: {old_progress}% -> {progress_percent}%"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update progress for issue {issue_id}: {e}")
            return False

    def complete_issue(self, issue_id: str) -> bool:
        """Mark an issue as complete.

        Args:
            issue_id: Issue identifier

        Returns:
            True if issue was marked complete, False otherwise
        """
        try:
            issue = self.roadmap_core.get_issue(issue_id)
            if not issue:
                logger.warning(f"Issue {issue_id} not found for completion")
                return False

            # Mark as complete
            old_status = issue.status
            issue.status = Status.DONE
            issue.progress_percentage = 100.0
            issue.completed_date = datetime.now().isoformat()
            issue.updated = datetime.now()

            # Save the issue
            issue_path = self.roadmap_core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

            logger.info(f"Completed issue {issue_id}: {old_status} -> {issue.status}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete issue {issue_id}: {e}")
            return False

    def track_branch(self, branch_name: str) -> dict[str, list[str]]:
        """Track a specific branch for issue associations.

        Args:
            branch_name: Name of the git branch to track

        Returns:
            Dictionary mapping issue IDs to actions taken
        """
        results = {}

        # Extract issue IDs from branch name
        issue_ids = self.extract_issue_ids_from_branch(branch_name)

        for issue_id in issue_ids:
            actions = []

            # Add branch association
            if self.add_branch_to_issue(issue_id, branch_name):
                actions.append("Added branch association")

            # Auto-start issue if configured
            if self.config.auto_start_on_branch:
                issue = self.roadmap_core.get_issue(issue_id)
                if issue and issue.status == Status.TODO:
                    issue.status = Status.IN_PROGRESS
                    issue.actual_start_date = datetime.now()
                    issue.updated = datetime.now()

                    # Save using the same pattern as RoadmapCore.update_issue
                    issue_path = self.roadmap_core.issues_dir / issue.filename
                    IssueParser.save_issue_file(issue, issue_path)

                    actions.append("Auto-started issue")

            results[issue_id] = actions

        return results

    def track_commit(
        self, commit_sha: str, commit_message: str | None = None
    ) -> dict[str, list[str]]:
        """Track a specific commit for issue associations.

        Args:
            commit_sha: Git commit SHA
            commit_message: Optional commit message (will be fetched if not provided)

        Returns:
            Dictionary mapping issue IDs to actions taken
        """
        results = {}

        # Get commit message if not provided
        if not commit_message:
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%s", commit_sha],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commit_message = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning(f"Could not retrieve commit message for {commit_sha}")
                commit_message = ""

        # Extract issue IDs from commit message
        issue_ids = self.extract_issue_ids_from_commit(commit_message)

        # Parse progress and completion markers
        progress_percent = self.parse_progress_marker(commit_message)

        for issue_id in issue_ids:
            actions = []

            # Add commit association
            if self.add_commit_to_issue(issue_id, commit_sha, commit_message):
                actions.append("Added commit association")

            # Update progress if marker found
            if progress_percent is not None:
                if self.update_issue_progress(issue_id, progress_percent):
                    actions.append(f"Updated progress to {progress_percent}%")

            # Check for completion marker
            if self.parse_completion_marker(commit_message, issue_id):
                if self.complete_issue(issue_id):
                    actions.append("Marked issue as complete")

            results[issue_id] = actions

        return results

    def scan_branches(self) -> dict[str, int]:
        """Scan all branches for issue associations.

        Returns:
            Summary of associations created per issue
        """
        branch_count = {}
        branches = self.get_all_branches()

        for branch in branches:
            issue_ids = self.extract_issue_ids_from_branch(branch.name)
            for issue_id in issue_ids:
                if self.add_branch_to_issue(issue_id, branch.name):
                    branch_count[issue_id] = branch_count.get(issue_id, 0) + 1

        return branch_count

    def scan_repository_history(self, max_commits: int = 1000) -> dict[str, int]:
        """Scan repository commit history for issue associations.

        Args:
            max_commits: Maximum number of commits to scan

        Returns:
            Summary of associations created per issue
        """
        commit_count = {}

        try:
            # Get commit history
            result = subprocess.run(
                ["git", "log", f"--max-count={max_commits}", "--format=%H|%s"],
                capture_output=True,
                text=True,
                check=True,
            )

            for line in result.stdout.strip().split("\n"):
                if "|" not in line:
                    continue

                commit_sha, commit_message = line.split("|", 1)

                # Extract issue IDs from commit message
                issue_ids = self.extract_issue_ids_from_commit(commit_message)

                for issue_id in issue_ids:
                    if self.add_commit_to_issue(issue_id, commit_sha, commit_message):
                        commit_count[issue_id] = commit_count.get(issue_id, 0) + 1

        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not scan repository history")

        return commit_count


class CIAutomation:
    """Handles automatic issue status updates based on CI/CD events."""

    def __init__(self, roadmap_core: RoadmapCore, tracker: CITracker):
        """Initialize CI automation.

        Args:
            roadmap_core: Core roadmap functionality
            tracker: CI tracking engine
        """
        self.roadmap_core = roadmap_core
        self.tracker = tracker
        self.config = tracker.config

    def on_branch_created(self, branch_name: str) -> dict[str, Any]:
        """Handle branch creation event.

        Args:
            branch_name: Name of the created branch

        Returns:
            Summary of actions taken
        """
        results = {
            "branch_name": branch_name,
            "issue_associations": {},
            "auto_actions": [],
        }

        # Track the branch
        associations = self.tracker.track_branch(branch_name)
        results["issue_associations"] = associations

        return results

    def on_pull_request_opened(self, pr_info: dict[str, Any]) -> dict[str, Any]:
        """Handle pull request opened event.

        Args:
            pr_info: Pull request information (branch, number, etc.)

        Returns:
            Summary of actions taken
        """
        results = {
            "pr_number": pr_info.get("number"),
            "branch": pr_info.get("head_branch"),
            "actions": [],
        }

        branch_name = pr_info.get("head_branch")
        if not branch_name:
            return results

        # Extract issue IDs and update status
        issue_ids = self.tracker.extract_issue_ids_from_branch(branch_name)

        for issue_id in issue_ids:
            if self.config.auto_progress_on_pr:
                issue = self.roadmap_core.get_issue(issue_id)
                if issue and issue.status == Status.TODO:
                    issue.status = Status.IN_PROGRESS
                    issue.actual_start_date = datetime.now()
                    issue.updated = datetime.now()

                    # Save using the same pattern as RoadmapCore.update_issue
                    issue_path = self.roadmap_core.issues_dir / issue.filename
                    IssueParser.save_issue_file(issue, issue_path)

                    results["actions"].append(f"Auto-started issue {issue_id}")

        return results

    def on_pull_request_merged(self, pr_info: dict[str, Any]) -> dict[str, Any]:
        """Handle pull request merged event.

        Args:
            pr_info: Pull request information (branch, base_branch, etc.)

        Returns:
            Summary of actions taken
        """
        results = {
            "pr_number": pr_info.get("number"),
            "branch": pr_info.get("head_branch"),
            "base_branch": pr_info.get("base_branch"),
            "actions": [],
        }

        branch_name = pr_info.get("head_branch")
        base_branch = pr_info.get("base_branch", "")

        if not branch_name:
            return results

        # Only auto-close if merging to main branch
        if base_branch not in self.config.main_branches:
            return results

        # Extract issue IDs and close if configured
        issue_ids = self.tracker.extract_issue_ids_from_branch(branch_name)

        for issue_id in issue_ids:
            if self.config.auto_close_on_merge:
                issue = self.roadmap_core.get_issue(issue_id)
                if issue and issue.status in [Status.IN_PROGRESS, Status.TODO]:
                    issue.status = Status.DONE
                    issue.actual_end_date = datetime.now()
                    issue.completed_date = datetime.now().isoformat()
                    issue.updated = datetime.now()

                    # Save using the same pattern as RoadmapCore.update_issue
                    issue_path = self.roadmap_core.issues_dir / issue.filename
                    IssueParser.save_issue_file(issue, issue_path)

                    results["actions"].append(f"Auto-completed issue {issue_id}")

        return results
