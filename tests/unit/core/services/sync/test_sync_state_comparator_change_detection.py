"""High-quality tests for SyncStateComparator with field-level change detection.

Focus: Validates conflict identification, update detection, field comparison.
"""

from datetime import UTC, datetime

import pytest

from roadmap.core.domain.issue import Issue, IssueType, Priority, Status
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator


@pytest.fixture
def comparator():
    """Create a SyncStateComparator instance."""
    return SyncStateComparator(
        fields_to_sync=["status", "assignee", "content", "labels"]
    )


@pytest.fixture
def local_issue():
    """Create a local Issue."""
    return Issue(
        id="issue-1",
        title="Local Title",
        status=Status.TODO,
        priority=Priority.MEDIUM,
        issue_type=IssueType.FEATURE,
        assignee="alice@example.com",
        milestone="v1-0",
        content="Local content",
        labels=["bug"],
        updated=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def remote_issue():
    """Create a remote issue dict."""
    return {
        "id": "issue-1",
        "title": "Remote Title",
        "status": "todo",
        "assignee": "alice@example.com",
        "content": "Remote content",
        "labels": ["bug"],
        "updated_at": datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
    }


class TestConflictIdentification:
    """Test conflict identification between local and remote."""

    def test_identifies_no_conflict_when_same(self, comparator):
        """Test no conflict when local and remote are identical."""
        # Create issues with identical content for both
        local_issue = Issue(
            id="issue-1",
            title="Same Title",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
            assignee="alice@example.com",
            milestone="v1-0",
            content="Same content",
            labels=["bug"],
            updated=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        )
        remote_issue = {
            "id": "issue-1",
            "title": "Same Title",
            "status": "todo",
            "assignee": "alice@example.com",
            "content": "Same content",
            "labels": ["bug"],
            "updated_at": datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        }

        local = {"issue-1": local_issue}
        remote = {"issue-1": remote_issue}

        conflicts = comparator.identify_conflicts(local, remote)

        assert len(conflicts) == 0

    def test_identifies_conflict_different_status(
        self, comparator, local_issue, remote_issue
    ):
        """Test conflict detected when status differs."""
        remote_issue["status"] = "in-progress"

        local = {"issue-1": local_issue}
        remote = {"issue-1": remote_issue}

        conflicts = comparator.identify_conflicts(local, remote)

        assert len(conflicts) == 1
        assert conflicts[0].issue_id == "issue-1"
        assert "status" in conflicts[0].field_names
