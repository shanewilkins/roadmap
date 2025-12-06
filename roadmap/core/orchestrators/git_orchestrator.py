"""Git integration orchestrator.

Handles Git operations and branch/commit integration with issues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...application.services import IssueService
    from ...infrastructure.git import GitIntegration


class GitOrchestrator:
    """Orchestrates Git integration operations."""

    def __init__(self, git: GitIntegration, issue_service: IssueService):
        """Initialize with Git and issue services.

        Args:
            git: GitIntegration instance
            issue_service: IssueService instance
        """
        self.git = git
        self.issue_service = issue_service

    def get_context(self) -> dict[str, Any]:
        """Get Git repository context information.

        Returns:
            Dictionary with Git repository information
        """
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
                issue = self.issue_service.get_issue(issue_id)
                if issue:
                    context["linked_issue"] = {
                        "id": issue.id,
                        "title": issue.title,
                        "status": issue.status.value,
                        "priority": issue.priority.value,
                    }

        return context

    def get_current_user(self) -> str | None:
        """Get current user from Git configuration.

        Returns:
            Current Git user identifier if available
        """
        return self.git.get_current_user()

    def create_issue_with_branch(
        self, issue_service: IssueService, title: str, **kwargs
    ) -> Any:
        """Create an issue and optionally create a Git branch for it.

        Args:
            issue_service: Issue service for creating the issue
            title: Issue title
            **kwargs: Additional issue arguments and git options

        Returns:
            Created Issue object if successful, None otherwise
        """
        # Extract git-specific arguments
        auto_create_branch = kwargs.pop("auto_create_branch", False)
        checkout_branch = kwargs.pop("checkout_branch", True)

        # Create the issue first
        issue = issue_service.create_issue(title, **kwargs)
        if not issue:
            return None

        # If we're in a Git repo and auto_create_branch is requested
        if auto_create_branch and self.git.is_git_repository():
            self.git.create_branch_for_issue(issue, checkout=checkout_branch)

        return issue

    def link_issue_to_current_branch(self, issue_id: str) -> bool:
        """Link an issue to the current Git branch.

        Args:
            issue_id: Issue identifier

        Returns:
            True if linking succeeded, False otherwise
        """
        if not self.git.is_git_repository():
            return False

        current_branch = self.git.get_current_branch()
        if not current_branch:
            return False

        issue = self.issue_service.get_issue(issue_id)
        if not issue:
            return False

        # Add branch information to issue metadata
        if not hasattr(issue, "git_branches"):
            issue.git_branches = []

        if current_branch.name not in issue.git_branches:
            issue.git_branches.append(current_branch.name)

        # Update the issue
        return (
            self.issue_service.update_issue(issue_id, git_branches=issue.git_branches)
            is not None
        )

    def get_commits_for_issue(self, issue_id: str, since: str | None = None) -> list:
        """Get Git commits that reference this issue.

        Args:
            issue_id: Issue identifier
            since: Only get commits since this date/ref

        Returns:
            List of commits referencing this issue
        """
        if not self.git.is_git_repository():
            return []

        return self.git.get_commits_for_issue(issue_id, since)

    def update_issue_from_git_activity(self, issue_id: str) -> bool:
        """Update issue progress and status based on Git commit activity.

        Args:
            issue_id: Issue identifier

        Returns:
            True if issue was updated, False otherwise
        """
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
            self.issue_service.update_issue(issue_id, **latest_updates)
            return True

        return False

    def suggest_branch_name(self, issue_id: str) -> str | None:
        """Suggest a branch name for an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            Suggested branch name, or None if not available
        """
        issue = self.issue_service.get_issue(issue_id)
        if not issue or not self.git.is_git_repository():
            return None

        return self.git.suggest_branch_name(issue)

    def get_linked_issues_by_branch(self) -> dict[str, list[str]]:
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
            if issue_id and self.issue_service.get_issue(issue_id):
                branch_issues[branch.name] = [issue_id]

        return branch_issues
