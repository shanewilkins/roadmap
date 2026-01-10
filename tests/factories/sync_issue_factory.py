"""Factory for creating test SyncIssue dataclass instances.

Provides sensible defaults and builder pattern for creating SyncIssue objects
in tests without dealing with dict construction.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from roadmap.core.models.sync_models import SyncIssue


class SyncIssueFactory:
    """Factory for creating test SyncIssue instances with sensible defaults."""

    # Default values
    DEFAULT_ID = "gh-1"
    DEFAULT_TITLE = "Test Issue"
    DEFAULT_STATUS = "open"
    DEFAULT_HEADLINE = "This is a test issue"
    DEFAULT_ASSIGNEE = "testuser"
    DEFAULT_MILESTONE = "v1.0"
    DEFAULT_BACKEND = "github"
    DEFAULT_BACKEND_ID = 1

    @staticmethod
    def create(
        id: str | None = None,
        title: str | None = None,
        status: str | None = None,
        headline: str | None = None,
        assignee: str | None = None,
        milestone: str | None = None,
        labels: list[str] | None = None,
        backend_name: str | None = None,
        backend_id: str | int | None = None,
        remote_ids: dict[str, str | int] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        custom_fields: dict[str, Any] | None = None,
        raw_response: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SyncIssue:
        """Create a SyncIssue with provided overrides and defaults.

        Args:
            id: Issue ID (default: "gh-1")
            title: Issue title (default: "Test Issue")
            status: Status like "open", "closed" (default: "open")
            headline: Short description (default: "This is a test issue")
            assignee: Assignee username (default: "testuser")
            milestone: Milestone name (default: "v1.0")
            labels: List of label names (default: [])
            backend_name: Backend name like "github" (default: "github")
            backend_id: Native backend ID (default: 1)
            remote_ids: Dict of backend -> remote_id (default: {})
            created_at: Creation timestamp (default: now - 30 days)
            updated_at: Update timestamp (default: now)
            custom_fields: Custom backend-specific fields (default: {})
            raw_response: Raw API response (default: {})
            metadata: Custom metadata (default: {})

        Returns:
            SyncIssue instance
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        return SyncIssue(
            id=id or SyncIssueFactory.DEFAULT_ID,
            title=title or SyncIssueFactory.DEFAULT_TITLE,
            status=status or SyncIssueFactory.DEFAULT_STATUS,
            headline=headline or SyncIssueFactory.DEFAULT_HEADLINE,
            assignee=assignee or SyncIssueFactory.DEFAULT_ASSIGNEE,
            milestone=milestone or SyncIssueFactory.DEFAULT_MILESTONE,
            labels=labels or [],
            backend_name=backend_name or SyncIssueFactory.DEFAULT_BACKEND,
            backend_id=backend_id if backend_id is not None else SyncIssueFactory.DEFAULT_BACKEND_ID,
            remote_ids=remote_ids or {},
            created_at=created_at or thirty_days_ago,
            updated_at=updated_at or now,
            custom_fields=custom_fields or {},
            raw_response=raw_response or {},
            metadata=metadata or {},
        )

    @staticmethod
    def create_minimal(
        id: str | None = None,
        title: str | None = None,
        status: str | None = None,
    ) -> SyncIssue:
        """Create a minimal SyncIssue with only required fields.

        Args:
            id: Issue ID (default: "gh-1")
            title: Issue title (default: "Test Issue")
            status: Status (default: "open")

        Returns:
            SyncIssue instance with minimal required fields
        """
        return SyncIssue(
            id=id or SyncIssueFactory.DEFAULT_ID,
            title=title or SyncIssueFactory.DEFAULT_TITLE,
            status=status or SyncIssueFactory.DEFAULT_STATUS,
        )

    @staticmethod
    def create_github(
        number: int,
        title: str | None = None,
        status: str | None = None,
        **kwargs: Any,
    ) -> SyncIssue:
        """Create a GitHub-specific SyncIssue.

        Args:
            number: GitHub issue number
            title: Issue title (default: "Test Issue")
            status: Status (default: "open")
            **kwargs: Additional fields passed to create()

        Returns:
            SyncIssue instance configured for GitHub
        """
        return SyncIssueFactory.create(
            id=f"gh-{number}",
            title=title or SyncIssueFactory.DEFAULT_TITLE,
            status=status or SyncIssueFactory.DEFAULT_STATUS,
            backend_name="github",
            backend_id=number,
            remote_ids={"github": number},
            **kwargs,
        )

    @staticmethod
    def create_batch(
        count: int,
        id_prefix: str = "gh-",
        title_prefix: str = "Issue",
        **kwargs: Any,
    ) -> list[SyncIssue]:
        """Create multiple SyncIssue instances for testing.

        Args:
            count: Number of issues to create
            id_prefix: Prefix for issue IDs (default: "gh-")
            title_prefix: Prefix for titles (default: "Issue")
            **kwargs: Additional fields passed to create()

        Returns:
            List of SyncIssue instances
        """
        return [
            SyncIssueFactory.create(
                id=f"{id_prefix}{i+1}",
                title=f"{title_prefix} {i+1}",
                backend_id=i + 1,
                remote_ids={SyncIssueFactory.DEFAULT_BACKEND: i + 1},
                **kwargs,
            )
            for i in range(count)
        ]

    @staticmethod
    def create_conflicting_pair(
        base_id: str = "gh-1",
        title: str | None = None,
    ) -> tuple[SyncIssue, SyncIssue]:
        """Create a pair of SyncIssue instances that would conflict.

        Useful for testing conflict detection and resolution.

        Args:
            base_id: Base ID for the issues
            title: Issue title

        Returns:
            Tuple of (local_version, remote_version) with conflicting changes
        """
        now = datetime.now(timezone.utc)

        local_issue = SyncIssueFactory.create(
            id=base_id,
            title=title or "Conflicting Issue",
            status="in_progress",
            assignee="local_user",
            updated_at=now - timedelta(minutes=5),
        )

        remote_issue = SyncIssueFactory.create(
            id=base_id,
            title=title or "Conflicting Issue",
            status="closed",  # Different status
            assignee="remote_user",  # Different assignee
            updated_at=now - timedelta(minutes=1),  # More recent
        )

        return local_issue, remote_issue

    @staticmethod
    def as_dict(sync_issue: SyncIssue) -> dict[str, Any]:
        """Convert SyncIssue to dictionary representation.

        Useful for testing code that still uses dicts temporarily.

        Args:
            sync_issue: SyncIssue instance

        Returns:
            Dictionary representation
        """
        return sync_issue.to_dict()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SyncIssue:
        """Create SyncIssue from dictionary representation.

        Args:
            data: Dictionary with issue data

        Returns:
            SyncIssue instance
        """
        return SyncIssue.from_dict(data)
