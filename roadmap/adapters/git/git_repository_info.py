"""Git repository information retrieval."""

import re
from pathlib import Path
from typing import Any

from roadmap.adapters.git.git_branch_manager import GitBranchManager
from roadmap.adapters.git.git_command_executor import GitCommandExecutor


class GitRepositoryInfo:
    """Retrieves Git repository information and user details."""

    def __init__(self, repo_path: Path | None = None):
        """Initialize repository info manager."""
        self.executor = GitCommandExecutor(repo_path)
        self.branch_manager = GitBranchManager(repo_path)

    def get_current_user(self) -> str | None:
        """Get current Git user name."""
        return self.executor.run(["config", "user.name"])

    def get_current_email(self) -> str | None:
        """Get current Git user email."""
        return self.executor.run(["config", "user.email"])

    def get_repository_info(self) -> dict[str, Any]:
        """Get general repository information.

        Returns:
            Dictionary with repo metadata: origin_url, github_owner, github_repo,
            current_branch, repo_root, total_commits
        """
        if not self.executor.is_git_repository():
            return {}

        info = {}

        # Remote origin URL
        origin_url = self.executor.run(["config", "--get", "remote.origin.url"])
        if origin_url:
            info["origin_url"] = origin_url

            # Try to extract GitHub repo info
            github_match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", origin_url)
            if github_match:
                info["github_owner"] = github_match.group(1)
                info["github_repo"] = github_match.group(2)

        # Current branch
        current_branch = self.branch_manager.get_current_branch()
        if current_branch:
            info["current_branch"] = current_branch.name

        # Repository root
        repo_root = self.executor.run(["rev-parse", "--show-toplevel"])
        if repo_root:
            info["repo_root"] = repo_root

        # Total commits
        commit_count = self.executor.run(["rev-list", "--count", "HEAD"])
        if commit_count:
            info["total_commits"] = int(commit_count)

        return info
