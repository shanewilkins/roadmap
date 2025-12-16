"""Git Integration Operations Module - Handles all git-related operations.

This module encapsulates git integration responsibilities extracted from RoadmapCore,
including branch management, commit tracking, and linking issues to branches.

Responsibilities:
- Git context retrieval
- Issue and branch linking
- Commit tracking for issues
- Branch name suggestions
- Git activity-based issue updates
"""

from typing import TYPE_CHECKING, Any

from roadmap.adapters.git.git import GitIntegration
from roadmap.common.errors.error_standards import OperationType, safe_operation
from roadmap.common.logging import get_logger

if TYPE_CHECKING:
    from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class GitIntegrationOps:
    """Manager for git integration operations."""

    def __init__(self, git: GitIntegration, core: "RoadmapCore"):
        """Initialize git integration operations manager.

        Args:
            git: The GitIntegration instance
            core: Reference to RoadmapCore instance for accessing core methods
        """
        self.git = git
        self.core = core

    @safe_operation(OperationType.READ, "GitRepository")
    def get_git_context(self) -> dict[str, Any]:
        """Get Git repository context information.

        Returns:
            Dictionary with git repository info, current branch, and linked issue info
        """
        logger.info("getting_git_context")
        if not self.git.is_git_repository():
            return {"is_git_repo": False}

        context: dict[str, Any] = {"is_git_repo": True}
        context.update(self.git.get_repository_info())

        # Current branch info
        current_branch = self.git.get_current_branch()
        if current_branch:
            context["current_branch"] = current_branch.name

            # Try to find linked issue
            issue_id = current_branch.extract_issue_id()
            if issue_id:
                issue = self.core.issues.get(issue_id)
                if issue:
                    context["linked_issue"] = {
                        "id": issue.id,
                        "title": issue.title,
                        "status": issue.status.value,
                        "priority": issue.priority.value,
                    }

        return context

    @safe_operation(OperationType.READ, "GitUser")
    def get_current_user_from_git(self) -> str | None:
        """Get current user from Git configuration.

        Returns:
            Current user name from git config, or None if not set
        """
        logger.info("getting_current_user_from_git")
        return self.git.get_current_user()

    @safe_operation(OperationType.CREATE, "GitBranch", include_traceback=True)
    def create_issue_with_git_branch(self, title: str, **kwargs):
        """Create an issue and optionally create a Git branch for it.

        Args:
            title: Issue title
            auto_create_branch: If True, create a branch for the issue (default: False)
            checkout_branch: If True, checkout the created branch (default: True)
            **kwargs: Additional issue creation parameters

        Returns:
            Created Issue object, or None if creation failed
        """
        logger.info(
            "creating_issue_with_git_branch",
            title=title,
            auto_create_branch=kwargs.get("auto_create_branch", False),
        )
        # Extract git-specific arguments
        auto_create_branch = kwargs.pop("auto_create_branch", False)
        checkout_branch = kwargs.pop("checkout_branch", True)

        # Create the issue first
        issue = self.core.issues.create(title, **kwargs)
        if not issue:
            return None

        # If we're in a Git repo and auto_create_branch is requested
        if auto_create_branch and self.git.is_git_repository():
            self.git.create_branch_for_issue(issue, checkout=checkout_branch)

        return issue

    @safe_operation(OperationType.UPDATE, "GitBranch")
    def link_issue_to_current_branch(self, issue_id: str) -> bool:
        """Link an issue to the current Git branch.

        Args:
            issue_id: The issue ID to link

        Returns:
            True if linking successful, False otherwise
        """
        logger.info("linking_issue_to_current_branch", issue_id=issue_id)
        if not self.git.is_git_repository():
            return False

        current_branch = self.git.get_current_branch()
        if not current_branch:
            return False

        issue = self.core.issues.get(issue_id)
        if not issue:
            return False

        # Add branch information to issue metadata
        if not hasattr(issue, "git_branches"):
            issue.git_branches = []

        if current_branch.name not in issue.git_branches:
            issue.git_branches.append(current_branch.name)

        # Update the issue
        return (
            self.core.issues.update(issue_id, git_branches=issue.git_branches)
            is not None
        )

    @safe_operation(OperationType.READ, "GitCommit")
    def get_commits_for_issue(self, issue_id: str, since: str | None = None) -> list:
        """Get Git commits that reference this issue.

        Args:
            issue_id: The issue ID to find commits for
            since: Optional date filter for commits

        Returns:
            List of commits referencing the issue
        """
        logger.info(
            "getting_commits_for_issue",
            issue_id=issue_id,
            has_since_filter=since is not None,
        )
        if not self.git.is_git_repository():
            return []

        return self.git.get_commits_for_issue(issue_id, since)

    @safe_operation(OperationType.UPDATE, "Issue")
    def update_issue_from_git_activity(self, issue_id: str) -> bool:
        """Update issue progress and status based on Git commit activity.

        Args:
            issue_id: The issue ID to update

        Returns:
            True if issue was updated, False otherwise
        """
        logger.info("updating_issue_from_git_activity", issue_id=issue_id)
        if not self.git.is_git_repository():
            return False

        commits = self.get_commits_for_issue(issue_id)
        if not commits:
            return False

        # Get the most recent commit with roadmap updates
        latest_updates = {}
        for commit in commits:
            updates = self.git.parse_commit_message_for_updates(commit)
            if updates:
                latest_updates.update(updates)

        if latest_updates:
            # Update the issue with the extracted information
            self.core.issues.update(issue_id, **latest_updates)
            return True

        return False

    def suggest_branch_name_for_issue(self, issue_id: str) -> str | None:
        """Suggest a branch name for an issue.

        Args:
            issue_id: The issue ID to suggest a branch name for

        Returns:
            Suggested branch name, or None if issue not found or not in git repo
        """
        issue = self.core.issues.get(issue_id)
        if not issue or not self.git.is_git_repository():
            return None

        return self.git.suggest_branch_name(issue)

    def get_branch_linked_issues(self) -> dict[str, list[str]]:
        """Get mapping of branches to their linked issue IDs.

        Returns:
            Dictionary mapping branch names to lists of issue IDs
        """
        if not self.git.is_git_repository():
            return {}

        branches = self.git.get_all_branches()
        branch_issues = {}

        for branch in branches:
            issue_id = branch.extract_issue_id()
            if issue_id and self.core.issues.get(issue_id):
                branch_issues[branch.name] = [issue_id]

        return branch_issues
