"""Factory for creating test Issue instances with sensible defaults.

This module provides a factory pattern for constructing Issue objects in tests,
eliminating duplication of Issue creation code across the test suite.

Usage:
    from tests.fixtures.issue_factory import IssueFactory

    # Create basic issue
    issue = IssueFactory.create(id="test-1", title="My Issue")

    # Create with specific status
    in_progress = IssueFactory.create_in_progress()

    # Create batch for collection testing
    issues = IssueFactory.create_batch(count=5)
"""

from roadmap.core.domain import Issue, IssueType, Priority, Status


class IssueFactory:
    """Factory for creating test Issue instances with common defaults.

    Provides convenience methods for creating issues with different statuses
    and configurations, reducing boilerplate in test files.
    """

    @staticmethod
    def create(
        id: str = "issue-1",
        title: str = "Test Issue",
        status: Status = Status.TODO,
        priority: Priority = Priority.MEDIUM,
        issue_type: IssueType = IssueType.FEATURE,
        assignee: str | None = None,
        milestone: str | None = None,
        content: str = "",
        labels: list[str] | None = None,
        progress_percentage: float | None = None,
        **kwargs,
    ) -> Issue:
        """Create an Issue with sensible defaults.

        Args:
            id: Issue identifier (default: "issue-1")
            title: Issue title (default: "Test Issue")
            status: Issue status (default: Status.TODO)
            priority: Issue priority (default: Priority.MEDIUM)
            issue_type: Issue type (default: IssueType.FEATURE)
            assignee: Optional assignee email
            milestone: Optional milestone name
            content: Issue description content
            labels: Optional list of labels
            progress_percentage: Progress percentage (0-100)
            **kwargs: Additional Issue constructor arguments

        Returns:
            Configured Issue instance
        """
        return Issue(
            id=id,
            title=title,
            status=status,
            priority=priority,
            issue_type=issue_type,
            assignee=assignee,
            milestone=milestone,
            content=content,
            labels=labels or [],
            progress_percentage=progress_percentage,
            **kwargs,
        )

    @staticmethod
    def create_todo(id: str = "issue-1", **kwargs) -> Issue:
        """Create a TODO status issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with TODO status
        """
        return IssueFactory.create(id=id, status=Status.TODO, **kwargs)

    @staticmethod
    def create_in_progress(id: str = "issue-1", **kwargs) -> Issue:
        """Create an IN_PROGRESS status issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with IN_PROGRESS status
        """
        return IssueFactory.create(
            id=id, status=Status.IN_PROGRESS, progress_percentage=50.0, **kwargs
        )

    @staticmethod
    def create_closed(id: str = "issue-1", **kwargs) -> Issue:
        """Create a CLOSED status issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with CLOSED status and 100% progress
        """
        return IssueFactory.create(
            id=id, status=Status.CLOSED, progress_percentage=100.0, **kwargs
        )

    @staticmethod
    def create_blocked(id: str = "issue-1", **kwargs) -> Issue:
        """Create a BLOCKED status issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with BLOCKED status
        """
        return IssueFactory.create(id=id, status=Status.BLOCKED, **kwargs)

    @staticmethod
    def create_high_priority(id: str = "issue-1", **kwargs) -> Issue:
        """Create a high priority issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with HIGH priority
        """
        return IssueFactory.create(id=id, priority=Priority.HIGH, **kwargs)

    @staticmethod
    def create_bug(id: str = "issue-1", **kwargs) -> Issue:
        """Create a bug type issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with BUG issue_type
        """
        return IssueFactory.create(id=id, issue_type=IssueType.BUG, **kwargs)

    @staticmethod
    def create_feature(id: str = "issue-1", **kwargs) -> Issue:
        """Create a feature type issue.

        Args:
            id: Issue identifier
            **kwargs: Additional arguments passed to create()

        Returns:
            Issue with FEATURE issue_type
        """
        return IssueFactory.create(id=id, issue_type=IssueType.FEATURE, **kwargs)

    @staticmethod
    def create_batch(
        count: int = 5,
        id_prefix: str = "issue",
        status: Status = Status.TODO,
        **kwargs,
    ) -> list[Issue]:
        """Create multiple issues for batch testing.

        Args:
            count: Number of issues to create (default: 5)
            id_prefix: Prefix for issue IDs (e.g., "issue-1", "issue-2")
            status: Status for all created issues
            **kwargs: Additional arguments passed to create()

        Returns:
            List of configured Issue instances
        """
        return [
            IssueFactory.create(
                id=f"{id_prefix}-{i}",
                status=status,
                **kwargs,
            )
            for i in range(1, count + 1)
        ]
