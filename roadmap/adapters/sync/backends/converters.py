"""Converters between Issue domain objects and GitHub API payloads.

This module handles bidirectional conversion:
- Issue → GitHub API payload (for push)
- GitHub API response → Issue (for pull)
"""

from typing import Any

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue


class IssueToGitHubPayloadConverter:
    """Convert Issue domain object to GitHub API payload."""

    @staticmethod
    def to_create_payload(issue: Issue) -> dict[str, Any]:
        """Convert Issue to GitHub API payload for create_issue().

        Args:
            issue: The Issue domain object

        Returns:
            Dictionary suitable for GitHub API create_issue() call
            (does NOT include 'state' - that's only for updates)
        """
        payload: dict[str, Any] = {
            "title": issue.title,
            "body": issue.content or "",  # Use content as description
        }

        # NOTE: labels field requires labels to exist in the repository
        # GitHub API validation fails if we send labels that don't exist
        # Skip labels for now until we have proper label validation
        # if issue.labels:
        #     payload["labels"] = issue.labels

        # NOTE: assignees must be valid collaborators on the repository
        # GitHub API validation fails if we send invalid usernames
        # Skip assignees for now until we have proper assignee validation
        # if issue.assignee and isinstance(issue.assignee, str) and issue.assignee.strip():
        #     payload["assignees"] = [issue.assignee]

        # NOTE: milestone field requires a milestone number/ID, not a string name
        # GitHub API validation fails if we send milestone names instead of numbers
        # Skip milestone for now until we have proper milestone mapping
        # if issue.milestone:
        #     payload["milestone"] = issue.milestone

        return payload

    @staticmethod
    def to_update_payload(issue: Issue) -> dict[str, Any]:
        """Convert Issue to GitHub API payload for update_issue().

        Args:
            issue: The Issue domain object

        Returns:
            Dictionary suitable for GitHub API update_issue() call
        """
        payload: dict[str, Any] = {
            "title": issue.title,
            "body": issue.content or "",  # Use content as description
        }

        # Map roadmap status to GitHub state (only on update)
        # GitHub only has open/closed, so we map our status accordingly
        if issue.status == Status.CLOSED:
            payload["state"] = "closed"
        else:
            payload["state"] = "open"

        # NOTE: labels field requires labels to exist in the repository
        # GitHub API validation fails if we send labels that don't exist
        # Skip labels for now until we have proper label validation
        # if issue.labels:
        #     payload["labels"] = issue.labels

        # NOTE: assignees must be valid collaborators on the repository
        # GitHub API validation fails if we send invalid usernames
        # Skip assignees for now until we have proper assignee validation
        # if issue.assignee and isinstance(issue.assignee, str) and issue.assignee.strip():
        #     payload["assignees"] = [issue.assignee]

        # NOTE: milestone field requires a milestone number/ID, not a string name
        # GitHub API validation fails if we send milestone names instead of numbers
        # Skip milestone for now until we have proper milestone mapping
        # if issue.milestone:
        #     payload["milestone"] = issue.milestone

        return payload

    @staticmethod
    def to_payload(issue: Issue, github_number: int | None = None) -> dict[str, Any]:
        """Convert Issue to GitHub API payload for create or update.

        Args:
            issue: The Issue domain object
            github_number: Optional GitHub issue number for update (None for create)

        Returns:
            Dictionary suitable for GitHub API create_issue or update_issue call
        """
        # Delegate to specific methods based on whether this is create or update
        if github_number:
            return IssueToGitHubPayloadConverter.to_update_payload(issue)
        else:
            return IssueToGitHubPayloadConverter.to_create_payload(issue)

    @staticmethod
    def get_github_number(issue: Issue) -> int | None:
        """Extract GitHub issue number from Issue's remote_ids.

        Args:
            issue: The Issue domain object

        Returns:
            GitHub issue number if linked, None otherwise
        """
        if issue.remote_ids and "github" in issue.remote_ids:
            github_id = issue.remote_ids["github"]
            # Convert to int if needed
            if isinstance(github_id, str):
                try:
                    return int(github_id)
                except ValueError:
                    return None
            return github_id
        return None


class GitHubPayloadToIssueConverter:
    """Convert GitHub API response to Issue domain object."""

    @staticmethod
    def from_sync_issue(sync_issue: SyncIssue) -> Issue:
        """Convert SyncIssue to Issue domain object.

        Args:
            sync_issue: The SyncIssue from GitHub fetch

        Returns:
            Issue domain object
        """
        # Map GitHub state to roadmap status
        # SyncIssue.status is already normalized: "open" or "closed"
        status = Status.CLOSED if sync_issue.status == "closed" else Status.TODO

        issue = Issue(
            title=sync_issue.title,
            content=sync_issue.headline or "",  # headline is the content in SyncIssue
            status=status,
            labels=sync_issue.labels or [],
            assignee=sync_issue.assignee,
            milestone=sync_issue.milestone,
        )

        # Store the GitHub issue number as remote_id
        # Use backend_id if available, or look in remote_ids dict
        github_number = sync_issue.backend_id or sync_issue.remote_ids.get("github")
        if github_number:
            issue.remote_ids["github"] = int(github_number) if isinstance(github_number, str) else github_number

        return issue

    @staticmethod
    def from_github_dict(github_dict: dict[str, Any]) -> Issue:
        """Convert GitHub API issue dict to Issue domain object.

        Args:
            github_dict: Dictionary from GitHub API response

        Returns:
            Issue domain object
        """
        # Map GitHub state to roadmap status
        status = Status.CLOSED if github_dict.get("state") == "closed" else Status.TODO

        # Extract assignee (GitHub returns list)
        assignees = github_dict.get("assignees") or []
        assignee = assignees[0]["login"] if assignees else None

        issue = Issue(
            title=github_dict.get("title", ""),
            content=github_dict.get("body") or "",
            status=status,
            labels=[label["name"] for label in (github_dict.get("labels") or [])],
            assignee=assignee,
            milestone=github_dict.get("milestone", {}).get("title") if github_dict.get("milestone") else None,
        )

        # Store GitHub issue number
        if "number" in github_dict:
            issue.remote_ids["github"] = github_dict["number"]

        return issue
