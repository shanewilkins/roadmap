"""High-quality tests for SyncConflictResolver with strategy validation.

Focus: Validates strategy routing, timestamp-based auto-merge logic, batch operations.
"""

from datetime import UTC, datetime

import pytest

from roadmap.core.domain.issue import Issue, Status
from roadmap.core.services.sync.sync_conflict_resolver import (
    Conflict,
    ConflictField,
    ConflictStrategy,
    SyncConflictResolver,
)


@pytest.fixture
def resolver():
    """Create a SyncConflictResolver instance."""
    return SyncConflictResolver()


@pytest.fixture
def local_issue():
    """Create a local Issue for testing."""
    return Issue(
        id="TEST-1",
        title="Local Title",
        status=Status.IN_PROGRESS,
        assignee="alice@example.com",
        milestone="v1-0",
        content="Local description",
    )


@pytest.fixture
def remote_issue_dict():
    """Create a remote issue dict for testing."""
    return {
        "id": "TEST-1",
        "title": "Remote Title",
        "status": "closed",
        "assignee": "bob@example.com",
        "milestone": "v2-0",
        "description": "Remote description",
    }


def create_conflict(
    issue_id="TEST-1",
    local_issue=None,
    remote_issue=None,
    fields=None,
    local_updated=None,
    remote_updated=None,
):
    """Helper to create a Conflict object."""
    if local_issue is None:
        local_issue = Issue(
            id=issue_id,
            title="Local",
            status=Status.TODO,
            content="Local",
        )

    if remote_issue is None:
        remote_issue = {
            "id": issue_id,
            "title": "Remote",
            "status": "open",
            "description": "Remote",
        }

    if fields is None:
        fields = [
            ConflictField(
                field_name="title",
                local_value=local_issue.title,
                remote_value=remote_issue.get("title"),
            )
        ]

    if local_updated is None:
        local_updated = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)

    return Conflict(
        issue_id=issue_id,
        local_issue=local_issue,
        remote_issue=remote_issue,
        fields=fields,
        local_updated=local_updated,
        remote_updated=remote_updated,
    )


class TestKeepLocalStrategy:
    """Test KEEP_LOCAL strategy: always return local issue."""

    def test_keep_local_returns_local_issue(
        self, resolver, local_issue, remote_issue_dict
    ):
        """Test that KEEP_LOCAL returns the local issue unchanged."""
        conflict = create_conflict(
            local_issue=local_issue,
            remote_issue=remote_issue_dict,
        )

        result = resolver.resolve(conflict, ConflictStrategy.KEEP_LOCAL)

        assert result == local_issue
        assert result.title == "Local Title"
        assert result.status == Status.IN_PROGRESS
        assert result.assignee == "alice@example.com"

    def test_keep_local_ignores_remote_values(self, resolver):
        """Test that KEEP_LOCAL doesn't use any remote values."""
        local = Issue(
            id="TEST-1",
            title="Keep This",
            status=Status.TODO,
            content="Keep This",
        )
        remote = {
            "id": "TEST-1",
            "title": "Ignore This",
            "status": "closed",
            "content": "Ignore This",
        }

        conflict = create_conflict(local_issue=local, remote_issue=remote)
        result = resolver.resolve(conflict, ConflictStrategy.KEEP_LOCAL)

        # All values should be from local, not remote
        assert result.title == "Keep This"
        assert result.status == Status.TODO
        assert result.content == "Keep This"
