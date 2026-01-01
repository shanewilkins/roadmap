"""Test data factories for sync functionality.

Provides builders for constructing test data without hardcoding,
enabling clear, maintainable, and reusable test scenarios.
"""

from datetime import datetime, timedelta
from typing import Any

from roadmap.common.constants import Priority, Status
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain.issue import Issue


class IssueTestDataBuilder:
    """Builder for constructing Issue instances for testing."""

    def __init__(self, base_id: str = "test-1"):
        """Initialize builder with default values.

        Args:
            base_id: Base ID for the issue (default: test-1)
        """
        self._id = base_id
        self._title = "Test Issue"
        self._priority = Priority.MEDIUM
        self._status = Status.TODO
        self._created = now_utc()
        self._updated = now_utc()
        self._content = ""
        self._labels: list[str] = []
        self._assignee: str | None = None
        self._github_issue: int | None = None
        self._github_sync_metadata: dict[str, Any] | None = None
        self._depends_on: list[str] = []
        self._blocks: list[str] = []

    def with_id(self, issue_id: str) -> "IssueTestDataBuilder":
        """Set the issue ID.

        Args:
            issue_id: The ID to assign

        Returns:
            Self for fluent chaining
        """
        self._id = issue_id
        return self

    def with_title(self, title: str) -> "IssueTestDataBuilder":
        """Set the issue title.

        Args:
            title: The title to assign

        Returns:
            Self for fluent chaining
        """
        self._title = title
        return self

    def with_priority(self, priority: Priority) -> "IssueTestDataBuilder":
        """Set the issue priority.

        Args:
            priority: The priority to assign

        Returns:
            Self for fluent chaining
        """
        self._priority = priority
        return self

    def with_status(self, status: Status) -> "IssueTestDataBuilder":
        """Set the issue status.

        Args:
            status: The status to assign

        Returns:
            Self for fluent chaining
        """
        self._status = status
        return self

    def with_content(self, content: str) -> "IssueTestDataBuilder":
        """Set the issue content.

        Args:
            content: The markdown content to assign

        Returns:
            Self for fluent chaining
        """
        self._content = content
        return self

    def with_labels(self, labels: list[str]) -> "IssueTestDataBuilder":
        """Set the issue labels.

        Args:
            labels: List of labels to assign

        Returns:
            Self for fluent chaining
        """
        self._labels = labels
        return self

    def with_assignee(self, assignee: str) -> "IssueTestDataBuilder":
        """Set the issue assignee.

        Args:
            assignee: The assignee to assign

        Returns:
            Self for fluent chaining
        """
        self._assignee = assignee
        return self

    def with_github_issue(self, issue_number: int) -> "IssueTestDataBuilder":
        """Set the GitHub issue number.

        Args:
            issue_number: The GitHub issue number

        Returns:
            Self for fluent chaining
        """
        self._github_issue = issue_number
        return self

    def with_created_at(self, dt: datetime) -> "IssueTestDataBuilder":
        """Set the creation timestamp.

        Args:
            dt: The datetime to set

        Returns:
            Self for fluent chaining
        """
        self._created = dt
        return self

    def with_updated_at(self, dt: datetime) -> "IssueTestDataBuilder":
        """Set the last updated timestamp.

        Args:
            dt: The datetime to set

        Returns:
            Self for fluent chaining
        """
        self._updated = dt
        return self

    def with_updated_minutes_ago(self, minutes: int) -> "IssueTestDataBuilder":
        """Set the updated timestamp to N minutes ago.

        Args:
            minutes: Number of minutes in the past

        Returns:
            Self for fluent chaining
        """
        self._updated = now_utc() - timedelta(minutes=minutes)
        return self

    def with_github_sync_metadata(
        self, metadata: dict[str, Any]
    ) -> "IssueTestDataBuilder":
        """Set the GitHub sync metadata.

        Args:
            metadata: The metadata dictionary

        Returns:
            Self for fluent chaining
        """
        self._github_sync_metadata = metadata
        return self

    def with_remote_id(self, remote_id: int) -> "IssueTestDataBuilder":
        """Set the remote ID in sync metadata.

        Args:
            remote_id: The remote issue ID

        Returns:
            Self for fluent chaining
        """
        if self._github_sync_metadata is None:
            self._github_sync_metadata = {}
        self._github_sync_metadata["remote_id"] = remote_id
        return self

    def with_last_synced(self, dt: datetime) -> "IssueTestDataBuilder":
        """Set the last sync time in metadata.

        Args:
            dt: The sync timestamp

        Returns:
            Self for fluent chaining
        """
        if self._github_sync_metadata is None:
            self._github_sync_metadata = {}
        self._github_sync_metadata["last_synced"] = dt.isoformat()
        return self

    def with_depends_on(self, issue_ids: list[str]) -> "IssueTestDataBuilder":
        """Set issues this one depends on.

        Args:
            issue_ids: List of issue IDs to depend on

        Returns:
            Self for fluent chaining
        """
        self._depends_on = issue_ids
        return self

    def with_blocks(self, issue_ids: list[str]) -> "IssueTestDataBuilder":
        """Set issues this one blocks.

        Args:
            issue_ids: List of issue IDs to block

        Returns:
            Self for fluent chaining
        """
        self._blocks = issue_ids
        return self

    def build(self) -> Issue:
        """Build and return the configured Issue.

        Returns:
            Constructed Issue instance

        Raises:
            ValueError: If required fields are invalid
        """
        return Issue(
            id=self._id,
            title=self._title,
            priority=self._priority,
            status=self._status,
            content=self._content,
            labels=self._labels,
            assignee=self._assignee,
            github_issue=self._github_issue,
            created=self._created,
            updated=self._updated,
            github_sync_metadata=self._github_sync_metadata,
            depends_on=self._depends_on,
            blocks=self._blocks,
        )


class SyncScenarioBuilder:
    """Builder for constructing sync test scenarios.

    Enables fluent construction of local and remote issue datasets
    for testing sync logic without hardcoding test data.
    """

    def __init__(self):
        """Initialize empty scenario."""
        self.local_issues: dict[str, Issue] = {}
        self.remote_issues: dict[str, dict[str, Any]] = {}

    def add_local_issue(self, issue: Issue) -> "SyncScenarioBuilder":
        """Add a local issue to the scenario.

        Args:
            issue: The Issue to add

        Returns:
            Self for fluent chaining
        """
        self.local_issues[issue.id] = issue
        return self

    def add_local_issue_builder(
        self, builder: IssueTestDataBuilder
    ) -> "SyncScenarioBuilder":
        """Build and add a local issue to the scenario.

        Args:
            builder: The builder to construct the issue from

        Returns:
            Self for fluent chaining
        """
        issue = builder.build()
        return self.add_local_issue(issue)

    def add_remote_issue(
        self, issue_id: str, remote_data: dict[str, Any]
    ) -> "SyncScenarioBuilder":
        """Add a remote issue to the scenario.

        Args:
            issue_id: The local issue ID this remote issue corresponds to
            remote_data: The remote issue data (dict representation)

        Returns:
            Self for fluent chaining
        """
        self.remote_issues[issue_id] = remote_data
        return self

    def add_new_remote_issue(
        self, remote_id: int, title: str, **kwargs
    ) -> "SyncScenarioBuilder":
        """Add a new remote issue (not in local).

        Args:
            remote_id: The remote issue number
            title: The issue title
            **kwargs: Additional remote issue fields

        Returns:
            Self for fluent chaining
        """
        # Create a synthetic ID for this remote issue
        synthetic_id = f"remote-{remote_id}"
        remote_data = {"id": remote_id, "title": title, **kwargs}
        return self.add_remote_issue(synthetic_id, remote_data)

    def build(self) -> tuple[dict[str, Issue], dict[str, dict[str, Any]]]:
        """Build and return the scenario.

        Returns:
            Tuple of (local_issues, remote_issues) dictionaries
        """
        return self.local_issues, self.remote_issues


class ConflictScenarioBuilder:
    """Builder for constructing conflict test scenarios."""

    def __init__(self):
        """Initialize empty conflict scenario."""
        self.conflicts: list[dict[str, Any]] = []
        self._next_issue_num = 1

    def add_title_conflict(
        self, local_title: str, remote_title: str
    ) -> "ConflictScenarioBuilder":
        """Add a title conflict scenario.

        Args:
            local_title: The local title
            remote_title: The remote title

        Returns:
            Self for fluent chaining
        """
        issue_id = f"conflict-{self._next_issue_num}"
        self._next_issue_num += 1

        local_issue = (
            IssueTestDataBuilder(issue_id)
            .with_title(local_title)
            .with_updated_minutes_ago(5)
            .build()
        )

        remote_issue = {
            "id": 100 + self._next_issue_num,
            "title": remote_title,
            "updated_at": (now_utc() - timedelta(minutes=10)).isoformat(),
        }

        self.conflicts.append(
            {
                "issue_id": issue_id,
                "local": local_issue,
                "remote": remote_issue,
                "field": "title",
                "local_value": local_title,
                "remote_value": remote_title,
            }
        )
        return self

    def add_status_conflict(
        self, local_status: Status, remote_status: str
    ) -> "ConflictScenarioBuilder":
        """Add a status conflict scenario.

        Args:
            local_status: The local status
            remote_status: The remote status (string)

        Returns:
            Self for fluent chaining
        """
        issue_id = f"conflict-{self._next_issue_num}"
        self._next_issue_num += 1

        local_issue = (
            IssueTestDataBuilder(issue_id)
            .with_status(local_status)
            .with_updated_minutes_ago(5)
            .build()
        )

        remote_issue = {
            "id": 100 + self._next_issue_num,
            "title": "Test",
            "status": remote_status,
            "updated_at": (now_utc() - timedelta(minutes=10)).isoformat(),
        }

        self.conflicts.append(
            {
                "issue_id": issue_id,
                "local": local_issue,
                "remote": remote_issue,
                "field": "status",
                "local_value": local_status,
                "remote_value": remote_status,
            }
        )
        return self

    def build(self) -> list[dict[str, Any]]:
        """Build and return conflict scenarios.

        Returns:
            List of conflict scenario dicts
        """
        return self.conflicts
