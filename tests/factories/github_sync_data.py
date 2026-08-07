"""Test data builders for GitHub sync functionality.

Provides factory builders for creating realistic test data structures used in
GitHub sync testing, following the factory pattern for maintainability and
reusability across the test suite.
"""

from datetime import UTC, datetime
from typing import Any


class IssueChangeTestBuilder:
    """Builder for creating IssueChange test data."""

    def __init__(self):
        """Initialize the builder with default values."""
        self.old_status: str = "todo"
        self.new_status: str = "in-progress"
        self.number: int = 123
        self.title: str = "Test Issue"
        self.body: str = "Test issue body"
        self.github_number: int = 100

    def with_status_change(self, old: str, new: str) -> "IssueChangeTestBuilder":
        """Set the status change."""
        self.old_status = old
        self.new_status = new
        return self

    def with_number(self, number: int) -> "IssueChangeTestBuilder":
        """Set the issue number."""
        self.number = number
        return self

    def with_title(self, title: str) -> "IssueChangeTestBuilder":
        """Set the issue title."""
        self.title = title
        return self

    def with_github_number(self, github_number: int) -> "IssueChangeTestBuilder":
        """Set the GitHub issue number."""
        self.github_number = github_number
        return self

    def build(self) -> dict[str, Any]:
        """Build the IssueChange dict."""
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "status_change": f"{self.old_status} -> {self.new_status}",
            "github_number": self.github_number,
        }


class MilestoneChangeTestBuilder:
    """Builder for creating MilestoneChange test data."""

    def __init__(self):
        """Initialize the builder with default values."""
        self.old_status: str = "open"
        self.new_status: str = "closed"
        self.number: int = 1
        self.title: str = "Test Milestone"
        self.github_number: int = 50

    def with_status_change(self, old: str, new: str) -> "MilestoneChangeTestBuilder":
        """Set the status change."""
        self.old_status = old
        self.new_status = new
        return self

    def with_number(self, number: int) -> "MilestoneChangeTestBuilder":
        """Set the milestone number."""
        self.number = number
        return self

    def with_title(self, title: str) -> "MilestoneChangeTestBuilder":
        """Set the milestone title."""
        self.title = title
        return self

    def with_github_number(self, github_number: int) -> "MilestoneChangeTestBuilder":
        """Set the GitHub milestone number."""
        self.github_number = github_number
        return self

    def build(self) -> dict[str, Any]:
        """Build the MilestoneChange dict."""
        return {
            "number": self.number,
            "title": self.title,
            "status_change": f"{self.old_status} -> {self.new_status}",
            "github_number": self.github_number,
        }


class SyncReportTestBuilder:
    """Builder for creating SyncReport test data."""

    def __init__(self):
        """Initialize the builder with default values."""
        self.detected_changes: list[dict] = []
        self.applied_changes: list[dict] = []
        self.conflicted_changes: list[dict] = []
        self.sync_timestamp: datetime = datetime.now(UTC)
        self.backend_type: str = "github"
        self.repo_owner: str = "test-owner"
        self.repo_name: str = "test-repo"

    def with_detected_issue_change(
        self, old: str, new: str, number: int = 1, title: str = "Issue"
    ) -> "SyncReportTestBuilder":
        """Add a detected issue change."""
        self.detected_changes.append(
            {
                "type": "issue",
                "number": number,
                "title": title,
                "status_change": f"{old} -> {new}",
            }
        )
        return self

    def with_applied_issue_change(
        self, old: str, new: str, number: int = 1, title: str = "Issue"
    ) -> "SyncReportTestBuilder":
        """Add an applied issue change."""
        self.applied_changes.append(
            {
                "type": "issue",
                "number": number,
                "title": title,
                "status_change": f"{old} -> {new}",
            }
        )
        return self

    def with_conflict(
        self, change_type: str, number: int, reason: str
    ) -> "SyncReportTestBuilder":
        """Add a conflicted change."""
        self.conflicted_changes.append(
            {"type": change_type, "number": number, "reason": reason}
        )
        return self

    def with_repo(self, owner: str, name: str) -> "SyncReportTestBuilder":
        """Set repository owner and name."""
        self.repo_owner = owner
        self.repo_name = name
        return self

    def build(self) -> dict[str, Any]:
        """Build the SyncReport dict."""
        return {
            "backend_type": self.backend_type,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "detected_changes": self.detected_changes,
            "applied_changes": self.applied_changes,
            "conflicted_changes": self.conflicted_changes,
            "sync_timestamp": self.sync_timestamp,
            "stats": {
                "detected_count": len(self.detected_changes),
                "applied_count": len(self.applied_changes),
                "conflicted_count": len(self.conflicted_changes),
            },
        }


class GitHubIssueTestBuilder:
    """Builder for creating GitHub API issue test data."""

    def __init__(self):
        """Initialize the builder with default values."""
        self.number: int = 1
        self.title: str = "Test Issue"
        self.body: str = "Issue body"
        self.state: str = "open"
        self.labels: list[str] = []
        self.assignees: list[str] = []
        self.milestone: dict[str, Any] | None = None

    def with_number(self, number: int) -> "GitHubIssueTestBuilder":
        """Set issue number."""
        self.number = number
        return self

    def with_title(self, title: str) -> "GitHubIssueTestBuilder":
        """Set issue title."""
        self.title = title
        return self

    def with_state(self, state: str) -> "GitHubIssueTestBuilder":
        """Set issue state (open/closed)."""
        self.state = state
        return self

    def with_labels(self, *labels: str) -> "GitHubIssueTestBuilder":
        """Set issue labels."""
        self.labels = list(labels)
        return self

    def with_assignees(self, *assignees: str) -> "GitHubIssueTestBuilder":
        """Set issue assignees."""
        self.assignees = list(assignees)
        return self

    def with_milestone(
        self, milestone_number: int, title: str
    ) -> "GitHubIssueTestBuilder":
        """Set issue milestone."""
        self.milestone = {"number": milestone_number, "title": title}
        return self

    def build(self) -> dict[str, Any]:
        """Build the GitHub issue dict."""
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": [{"name": label} for label in self.labels],
            "assignees": [{"login": assignee} for assignee in self.assignees],
            "milestone": self.milestone,
        }


class GitHubMilestoneTestBuilder:
    """Builder for creating GitHub API milestone test data."""

    def __init__(self):
        """Initialize the builder with default values."""
        self.number: int = 1
        self.title: str = "Test Milestone"
        self.state: str = "open"
        self.description: str = "Milestone description"
        self.open_issues: int = 5
        self.closed_issues: int = 3

    def with_number(self, number: int) -> "GitHubMilestoneTestBuilder":
        """Set milestone number."""
        self.number = number
        return self

    def with_title(self, title: str) -> "GitHubMilestoneTestBuilder":
        """Set milestone title."""
        self.title = title
        return self

    def with_state(self, state: str) -> "GitHubMilestoneTestBuilder":
        """Set milestone state (open/closed)."""
        self.state = state
        return self

    def with_issue_counts(
        self, open_count: int, closed_count: int
    ) -> "GitHubMilestoneTestBuilder":
        """Set issue counts."""
        self.open_issues = open_count
        self.closed_issues = closed_count
        return self

    def build(self) -> dict[str, Any]:
        """Build the GitHub milestone dict."""
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "description": self.description,
            "open_issues": self.open_issues,
            "closed_issues": self.closed_issues,
        }
