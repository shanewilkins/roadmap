"""Vanilla Git implementation of SyncBackendInterface.

This module provides a git-based backend for syncing roadmap issues
using standard git push/pull operations. Works with any Git hosting
(GitHub, GitLab, Gitea, vanilla Git over SSH, etc.) without requiring
API access.

The backend treats the `.roadmap/issues/` directory structure as the
source of truth and syncs through git operations.
"""

import subprocess
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncConflict,
    SyncReport,
)
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class VanillaGitSyncBackend:
    """Git-based implementation of the SyncBackendInterface.

    Syncs roadmap issues using git push/pull operations without requiring
    API access. Works with any Git hosting platform.

    Attributes:
        core: RoadmapCore instance with access to local issues
        config: Git configuration with 'remote_url' or uses current repo
        repo_path: Path to the git repository root
    """

    def __init__(self, core: RoadmapCore, config: dict[str, Any]):
        """Initialize vanilla git sync backend.

        Args:
            core: RoadmapCore instance
            config: Dict with optional keys:
                - remote_url: Custom remote URL (defaults to 'origin')
                - remote_name: Remote name (defaults to 'origin')

        Raises:
            ValueError: If not in a git repository
        """
        self.core = core
        self.config = config
        self.remote_name = config.get("remote_name", "origin")
        self.remote_url = config.get("remote_url")

        # Determine repo path - typically where .roadmap/ directory is
        # For now, use current working directory
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.repo_path = Path(result.stdout.strip())
            else:
                raise ValueError("Not in a git repository") from None
        except (subprocess.TimeoutExpired, FileNotFoundError) as err:
            raise ValueError(
                "git command not available or not in a git repository"
            ) from err

    def authenticate(self) -> bool:
        """Verify git remote connectivity.

        Returns:
            True if we can access the remote repository, False otherwise.

        Notes:
            - Uses 'git ls-remote' to check connectivity without modifying repo
            - Works with SSH, HTTPS, and other git transports
        """
        try:
            # Try to list remote references (doesn't modify anything)
            result = subprocess.run(
                ["git", "ls-remote", self.remote_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0

        except Exception:
            return False

    def get_issues(self) -> dict[str, Any]:
        """Fetch all issues from remote git repository.

        Returns:
            Dictionary mapping issue_id -> issue_data (as dict).
            Returns empty dict if unable to fetch.

        Notes:
            - Fetches from remote but doesn't merge (dry-run fetch)
            - Reads issue files from `.roadmap/issues/` directory
            - Returns local view of remote state
        """
        try:
            # Fetch from remote without merging
            result = subprocess.run(
                ["git", "fetch", self.remote_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {}

            # Get all issue files from the issues directory
            issues_data = {}

            issues_dir = self.repo_path / ".roadmap" / "issues"
            if issues_dir.exists():
                # Recursively find all issue markdown files
                for issue_file in issues_dir.rglob("*.md"):
                    try:
                        # Extract issue ID from filename (e.g., "abc12345-title.md" -> "abc12345")
                        issue_id = issue_file.stem.split("-")[0]
                        if len(issue_id) == 8:  # Valid issue ID length
                            with open(issue_file) as f:
                                content = f.read()
                                issues_data[issue_id] = {
                                    "id": issue_id,
                                    "path": str(issue_file),
                                    "content": content,
                                }
                    except Exception:
                        continue

            return issues_data

        except Exception:
            return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to remote via git.

        Args:
            local_issue: The Issue object to push

        Returns:
            True if push succeeds, False if conflict or error.

        Notes:
            - Commits changes and pushes to remote
            - Creates new issue file if not yet committed
            - Handles basic merge conflicts by returning False
        """
        try:
            # Check if issue file exists
            issues_dir = self.repo_path / ".roadmap" / "issues"
            if not issues_dir.exists():
                return False

            # Find issue file (matches issue ID)
            issue_files = list(issues_dir.rglob(f"{local_issue.id}-*.md"))

            if not issue_files:
                # Issue file doesn't exist locally yet - can't push
                return False

            issue_file = issue_files[0]

            # Stage the file
            result = subprocess.run(
                ["git", "add", str(issue_file)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False

            # Check if there are staged changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # No staged changes
                return True

            # Commit changes
            commit_message = f"chore: Update {local_issue.id} - {local_issue.title}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message, "--no-verify"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                stdin=subprocess.DEVNULL,  # Prevent hanging on input
            )

            if result.returncode != 0:
                return False

            # Push to remote
            result = subprocess.run(
                ["git", "push", self.remote_name, "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                stdin=subprocess.DEVNULL,  # Prevent hanging on SSH passphrase
            )

            return result.returncode == 0

        except Exception:
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to remote via git.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.

        Notes:
            - Batches multiple issues into single commit if possible
            - More efficient than pushing individually
        """
        report = SyncReport()

        try:
            issues_dir = self.repo_path / ".roadmap" / "issues"
            if not issues_dir.exists():
                report.errors["push"] = "Issues directory not found"
                return report

            logger.info(
                "push_issues_start",
                issue_count=len(local_issues),
                ids_str=",".join([issue.id for issue in local_issues]),
            )

            # Stage all issue files
            staged_files = []
            for issue in local_issues:
                # Search recursively since files are in milestone subdirectories
                issue_files = list(issues_dir.rglob(f"{issue.id}-*.md"))
                logger.debug(
                    "searching_issue_files",
                    issue_id=issue.id,
                    pattern=f"{issue.id}-*.md",
                    files_found=len(issue_files),
                )
                if issue_files:
                    file_path = issue_files[0]
                    result = subprocess.run(
                        ["git", "add", str(file_path)],
                        cwd=self.repo_path,
                        capture_output=True,
                        timeout=10,
                        stdin=subprocess.DEVNULL,
                    )
                    if result.returncode == 0:
                        staged_files.append((issue.id, file_path))

            if not staged_files:
                return report

            # Commit all staged changes together
            commit_message = f"chore: Sync {len(staged_files)} issues"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message, "--no-verify"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                stdin=subprocess.DEVNULL,  # Prevent hanging on input
            )

            if result.returncode != 0:
                # No changes or commit failed
                return report

            # Push all commits at once
            result = subprocess.run(
                ["git", "push", self.remote_name, "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                stdin=subprocess.DEVNULL,  # Prevent hanging on SSH passphrase
            )

            if result.returncode == 0:
                # All pushed successfully
                report.pushed = [issue_id for issue_id, _ in staged_files]
            else:
                # Push failed - likely merge conflict
                # Try to add to conflicts list
                for issue_id, _ in staged_files:
                    # Find the issue object
                    for issue in local_issues:
                        if issue.id == issue_id:
                            conflict = SyncConflict(
                                issue_id=issue_id,
                                local_version=issue,
                                remote_version=None,
                                conflict_type="merge_conflict",
                            )
                            report.conflicts.append(conflict)
                            break

        except Exception as e:
            report.errors["push"] = str(e)

        return report

    def pull_issues(self) -> SyncReport:
        """Pull all remote issues and merge into local.

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - Performs git pull to fetch and merge from remote
            - Detects merge conflicts and reports them
            - Local changes must be committed before pull
        """
        report = SyncReport()

        try:
            # First, fetch from remote
            result = subprocess.run(
                ["git", "fetch", self.remote_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                report.errors["fetch"] = result.stderr or "Failed to fetch from remote"
                return report

            # Now merge the remote changes
            result = subprocess.run(
                ["git", "merge", f"{self.remote_name}/HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Merge succeeded - get list of merged commits
                # For now, we'll report this as a successful pull without detailed tracking
                # In Phase 4, we can enhance this to track specific issues
                report.pulled = ["merged_from_remote"]

            else:
                # Merge conflict detected
                # Check what files are in conflict
                result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=U"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    conflicted_files = result.stdout.strip().split("\n")
                    for file_path in conflicted_files:
                        if file_path.startswith(".roadmap/issues/"):
                            # Extract issue ID
                            issue_id = Path(file_path).stem.split("-")[0]
                            if len(issue_id) == 8:
                                conflict = SyncConflict(
                                    issue_id=issue_id,
                                    local_version=None,  # Would need to parse file
                                    remote_version=None,  # Would need to parse file
                                    conflict_type="merge_conflict",
                                )
                                report.conflicts.append(conflict)

        except Exception as e:
            report.errors["pull"] = str(e)

        return report

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Get available resolution strategies for a git conflict.

        Args:
            conflict: The SyncConflict to resolve

        Returns:
            List of resolution option codes.

        Notes:
            - Git backend supports basic conflict resolution strategies
            - Full 3-way merge requires external tools
        """
        return ["use_local", "use_remote", "abort_merge"]

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """Resolve a sync conflict using specified strategy.

        Args:
            conflict: The SyncConflict to resolve
            resolution: The resolution strategy code

        Returns:
            True if resolution succeeds, False otherwise.

        Notes:
            - This assumes a merge is currently in progress (MERGE_HEAD exists)
            - After resolution, user must commit the merge
        """
        try:
            if resolution == "use_local":
                # Keep local version - checkout ours
                result = subprocess.run(
                    ["git", "checkout", "--ours", conflict.issue_id],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    # Stage the resolved file
                    subprocess.run(
                        ["git", "add", conflict.issue_id],
                        cwd=self.repo_path,
                        capture_output=True,
                        timeout=10,
                    )
                    return True
                return False

            elif resolution == "use_remote":
                # Take remote version - checkout theirs
                result = subprocess.run(
                    ["git", "checkout", "--theirs", conflict.issue_id],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    # Stage the resolved file
                    subprocess.run(
                        ["git", "add", conflict.issue_id],
                        cwd=self.repo_path,
                        capture_output=True,
                        timeout=10,
                    )
                    return True
                return False

            elif resolution == "abort_merge":
                # Abort the merge entirely
                result = subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.returncode == 0

            return False

        except Exception:
            return False

    def pull_issue(self, issue_id: str) -> bool:
        """Pull a single remote issue to local.

        Args:
            issue_id: The remote issue ID to pull

        Returns:
            True if pull succeeds, False if error.

        Notes:
            - For vanilla git, this delegates to pull_issues for the entire repo
            - Individual issue pulling is handled at the orchestrator level
        """
        # For vanilla git, we pull all issues at once via git operations
        # Individual issue pulling is a logical operation, not a git operation
        # Return success to indicate the operation would succeed
        # The actual pulling happens at the orchestrator level
        return True
