"""Factory functions for creating test data."""

from uuid import uuid4

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue


class IssueFactory:
    """Factory for creating test Issue objects."""

    @staticmethod
    def create(
        id: str | None = None,
        title: str = "Test Issue",
        status: Status | str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
        milestone: str | None = None,
        **kwargs,
    ) -> Issue:
        """Create a test Issue with sensible defaults."""
        # Convert string to Status enum if needed
        if isinstance(status, str):
            status = Status(status)
        status = status or Status.TODO

        return Issue(
            id=id or str(uuid4()),
            title=title,
            status=status,
            labels=labels or [],
            assignee=assignee,
            milestone=milestone,
            **kwargs,
        )


class SyncIssueFactory:
    """Factory for creating test SyncIssue objects (remote format)."""

    @staticmethod
    def create(
        id: str | None = None,
        title: str = "Test Remote Issue",
        status: str = "open",
        labels: list[str] | None = None,
        **kwargs,
    ) -> SyncIssue:
        """Create a test SyncIssue (remote format)."""
        return SyncIssue(
            id=id or f"github-{uuid4().hex[:8]}",
            title=title,
            status=status,
            labels=labels or [],
            **kwargs,
        )


class DuplicateSetFactory:
    """Factory for creating canonical issues with duplicates."""

    @staticmethod
    def create_canonical_with_duplicates(
        canonical_title: str = "Build feature X",
        num_local_duplicates: int = 2,
        num_remote_duplicates: int = 1,
    ) -> tuple[Issue, list[Issue], dict[str, SyncIssue]]:
        """Create a canonical issue with N local + N remote duplicates.

        Returns:
            Tuple of (canonical, local_duplicates, remote_duplicates_dict)
        """
        canonical = IssueFactory.create(title=canonical_title)

        local_dups = [
            IssueFactory.create(title=canonical_title)
            for _ in range(num_local_duplicates)
        ]

        remote_dups = {
            f"github-{i}": SyncIssueFactory.create(title=canonical_title)
            for i in range(num_remote_duplicates)
        }

        return canonical, local_dups, remote_dups
