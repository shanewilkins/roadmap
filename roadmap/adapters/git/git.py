"""Git integration module for enhanced Git workflow support."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.core.domain import Issue


@dataclass
class GitCommit:
    """Represents a Git commit with roadmap-relevant information."""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: list[str]
    insertions: int = 0
    deletions: int = 0

    @property
    def short_hash(self) -> str:
        """Get short commit hash."""
        return self.hash[:8]

    def extract_roadmap_references(self) -> list[str]:
        """Extract roadmap issue references from commit message."""
        # Enhanced patterns to support multiple formats:
        # 1. [roadmap:issue-id] or [closes roadmap:issue-id] (existing)
        # 2. fixes #issue-id, closes #issue-id (GitHub/GitLab style)
        # 3. resolves #issue-id, resolve #issue-id
        # 4. addresses #issue-id, refs #issue-id
        # Issue IDs can be hex or alphanumeric
        patterns = [
            # Original roadmap: patterns
            r"\[roadmap:([a-zA-Z0-9]{8,})\]",
            r"\[closes roadmap:([a-zA-Z0-9]{8,})\]",
            r"\[fixes roadmap:([a-zA-Z0-9]{8,})\]",
            r"roadmap:([a-zA-Z0-9]{8,})",
            # GitHub/GitLab style patterns
            r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#([a-zA-Z0-9]{8,})\b",
            r"\b(?:addresses?|refs?)\s+#([a-zA-Z0-9]{8,})\b",
            # Simple # references
            r"#([a-f0-9]{8})\b",  # Hex issue IDs only for this pattern to avoid false positives
        ]

        references = []
        for pattern in patterns:
            matches = re.findall(pattern, self.message, re.IGNORECASE)
            references.extend(matches)

        return list(set(references))  # Remove duplicates

    def extract_progress_info(self) -> float | None:
        """Extract progress percentage from commit message."""
        # Pattern: [progress:25%] or [progress:25]
        patterns = [
            r"\[progress:(\d+)%?\]",
            r"progress:(\d+)%?",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.message, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None


@dataclass
class GitBranch:
    """Represents a Git branch with roadmap integration info."""

    name: str
    current: bool = False
    remote: str | None = None
    last_commit: str | None = None

    def extract_issue_id(self) -> str | None:
        """Extract issue ID from branch name patterns."""
        # Common patterns:
        # feature/issue-abc12345-description
        # bugfix/abc12345-fix-login
        # abc12345-new-feature
        patterns = [
            r"(?:feature|bugfix|hotfix)/(?:issue-)?([a-f0-9]{8})",
            r"^([a-f0-9]{8})-",
            r"/([a-f0-9]{8})-",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.name, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def suggests_issue_type(self) -> str | None:
        """Suggest issue type based on branch name."""
        if self.name.startswith(("feature/", "feat/")):
            return "feature"
        elif self.name.startswith(("bugfix/", "bug/", "fix/")):
            return "bug"
        elif self.name.startswith(("hotfix/", "urgent/")):
            return "hotfix"
        elif self.name.startswith(("docs/", "doc/")):
            return "documentation"
        elif self.name.startswith(("test/", "tests/")):
            return "testing"

        return None


class GitIntegration:
    """Orchestrator for Git integration functionality.

    Coordinates branch management, commit analysis, and repository operations.
    Delegates to focused manager classes for each responsibility.
    """

    def __init__(self, repo_path: Path | None = None, config: object | None = None):
        """Initialize Git integration orchestrator."""
        from roadmap.adapters.git.git_branch_manager import GitBranchManager
        from roadmap.adapters.git.git_command_executor import GitCommandExecutor
        from roadmap.adapters.git.git_commit_analyzer import GitCommitAnalyzer
        from roadmap.adapters.git.git_repository_info import GitRepositoryInfo

        self.repo_path = repo_path or Path.cwd()
        self.config = config

        # Initialize managers
        self.executor = GitCommandExecutor(repo_path)
        self.branch_manager = GitBranchManager(repo_path, config)
        self.commit_analyzer = GitCommitAnalyzer(repo_path)
        self.repo_info = GitRepositoryInfo(repo_path)

    def is_git_repository(self) -> bool:
        """Check if current directory is in a Git repository."""
        return self.executor.is_git_repository()

    def get_current_user(self) -> str | None:
        """Get current Git user name."""
        return self.repo_info.get_current_user()

    def get_current_email(self) -> str | None:
        """Get current Git user email."""
        return self.repo_info.get_current_email()

    def get_current_branch(self) -> GitBranch | None:
        """Get information about the current branch."""
        return self.branch_manager.get_current_branch()

    def get_all_branches(self) -> list[GitBranch]:
        """Get all local branches."""
        return self.branch_manager.get_all_branches()

    def get_recent_commits(
        self, count: int = 10, since: str | None = None
    ) -> list[GitCommit]:
        """Get recent commits with detailed information."""
        return self.commit_analyzer.get_recent_commits(count, since)

    def get_commits_for_issue(
        self, issue_id: str, since: str | None = None
    ) -> list[GitCommit]:
        """Get all commits that reference a specific issue."""
        return self.commit_analyzer.get_commits_for_issue(issue_id, since)

    def suggest_branch_name(self, issue: Issue) -> str:
        """Suggest a branch name based on issue information."""
        return self.branch_manager.suggest_branch_name(issue)

    def create_branch_for_issue(
        self, issue: Issue, checkout: bool = True, force: bool = False
    ) -> bool:
        """Create a new branch for an issue."""
        return self.branch_manager.create_branch_for_issue(issue, checkout, force)

    def auto_create_issue_from_branch(
        self, roadmap_core, branch_name: str | None = None
    ) -> str | None:
        """Automatically create an issue from a branch name if one doesn't exist."""
        return self.branch_manager.auto_create_issue_from_branch(
            roadmap_core, branch_name
        )

    def get_repository_info(self) -> dict[str, Any]:
        """Get general repository information."""
        return self.repo_info.get_repository_info()

    def parse_commit_message_for_updates(self, commit: GitCommit) -> dict[str, Any]:
        """Parse commit message for roadmap updates."""
        return self.commit_analyzer.parse_commit_message_for_updates(commit)

    def auto_update_issues_from_commits(
        self, roadmap_core, commits: list[GitCommit] | None = None
    ) -> dict[str, list[str]]:
        """Automatically update issues based on commit messages."""
        return self.commit_analyzer.auto_update_issues_from_commits(
            roadmap_core, commits
        )

    def get_branch_linked_issues(self, branch_name: str) -> list[str]:
        """Get issue IDs linked to a specific branch."""
        return self.branch_manager.get_branch_linked_issues(branch_name)
