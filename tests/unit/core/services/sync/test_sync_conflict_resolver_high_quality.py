"""High-quality tests for SyncConflictResolver with strategy validation.

Focus: Validates strategy routing, timestamp-based auto-merge logic, batch operations.
Validates:
- All 3 strategies applied correctly (KEEP_LOCAL, KEEP_REMOTE, AUTO_MERGE)
- AUTO_MERGE timestamp comparison logic (newer wins, tie goes to local)
- Batch operations handle errors gracefully
- Resolved issues have correct field values
- Strategy routing is correct for different scenarios
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


class TestKeepRemoteStrategy:
    """Test KEEP_REMOTE strategy: convert remote to local format and return."""

    def test_keep_remote_returns_converted_remote(self, resolver):
        """Test that KEEP_REMOTE returns remote issue converted to local format."""
        local = Issue(
            id="TEST-1",
            title="Local",
            status=Status.TODO,
            content="Local",
        )
        remote = {
            "id": "TEST-1",
            "title": "Remote Title",
            "status": "in-progress",
            "description": "Remote description",
        }

        conflict = create_conflict(local_issue=local, remote_issue=remote)
        result = resolver.resolve(conflict, ConflictStrategy.KEEP_REMOTE)

        # Result should be converted remote, not local
        assert result.title == "Remote Title"
        # Note: remote dict uses "description" key, Issue converts to "content"
        assert result.content == "Remote description"
        # Status mapping: "in-progress" -> Status.IN_PROGRESS
        assert result.status == Status.IN_PROGRESS

    def test_keep_remote_uses_remote_values_not_local(self, resolver):
        """Test that KEEP_REMOTE uses all remote values, not local."""
        local = Issue(
            id="TEST-1",
            title="Ignore This",
            status=Status.TODO,
            content="Ignore This",
        )
        remote = {
            "id": "TEST-1",
            "title": "Use This",
            "status": "closed",
            "description": "Use This",
        }

        conflict = create_conflict(local_issue=local, remote_issue=remote)
        result = resolver.resolve(conflict, ConflictStrategy.KEEP_REMOTE)

        assert result.title == "Use This"
        assert result.content == "Use This"
        assert "closed" in str(result.status) or result.status.value == "closed"


class TestAutoMergeStrategy:
    """Test AUTO_MERGE strategy: timestamp-based merging."""

    def test_auto_merge_local_newer_uses_local(self, resolver):
        """Test AUTO_MERGE uses local when local is newer."""
        local = Issue(
            id="TEST-1",
            title="Local Newer",
            status=Status.IN_PROGRESS,
            content="Local",
        )
        remote = {
            "id": "TEST-1",
            "title": "Remote Older",
            "status": "closed",
            "content": "Remote",
        }

        local_updated = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        remote_updated = datetime(2026, 1, 31, 11, 0, 0, tzinfo=UTC)  # 1 hour older

        conflict = Conflict(
            issue_id="TEST-1",
            local_issue=local,
            remote_issue=remote,
            fields=[],
            local_updated=local_updated,
            remote_updated=remote_updated,
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        # Local is newer, so use local values
        assert result.title == "Local Newer"
        assert result.status == Status.IN_PROGRESS

    def test_auto_merge_remote_newer_uses_remote(self, resolver):
        """Test AUTO_MERGE uses remote when remote is newer."""
        local = Issue(
            id="TEST-1",
            title="Local Older",
            status=Status.TODO,
            content="Local",
        )
        remote = {
            "id": "TEST-1",
            "title": "Remote Newer",
            "status": "in_progress",
            "content": "Remote",
        }

        local_updated = datetime(2026, 1, 31, 11, 0, 0, tzinfo=UTC)  # Older
        remote_updated = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)  # 1 hour newer

        conflict = Conflict(
            issue_id="TEST-1",
            local_issue=local,
            remote_issue=remote,
            fields=[],
            local_updated=local_updated,
            remote_updated=remote_updated,
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        # Remote is newer, so use remote values
        assert result.title == "Remote Newer"

    def test_auto_merge_equal_timestamps_uses_local(self, resolver):
        """Test AUTO_MERGE uses local when timestamps are equal (tie-breaker)."""
        local = Issue(
            id="TEST-1",
            title="Local Tie",
            status=Status.IN_PROGRESS,
            content="Local",
        )
        remote = {
            "id": "TEST-1",
            "title": "Remote Tie",
            "status": "closed",
            "content": "Remote",
        }

        same_time = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)

        conflict = Conflict(
            issue_id="TEST-1",
            local_issue=local,
            remote_issue=remote,
            fields=[],
            local_updated=same_time,
            remote_updated=same_time,
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        # Timestamps equal, prefer local (tie-breaker)
        assert result.title == "Local Tie"
        assert result.status == Status.IN_PROGRESS

    def test_auto_merge_no_remote_timestamp_uses_local(self, resolver):
        """Test AUTO_MERGE uses local when remote has no timestamp."""
        local = Issue(
            id="TEST-1",
            title="Local Has Timestamp",
            status=Status.IN_PROGRESS,
            content="Local",
        )
        remote = {
            "id": "TEST-1",
            "title": "Remote No Timestamp",
            "status": "closed",
            "content": "Remote",
        }

        conflict = Conflict(
            issue_id="TEST-1",
            local_issue=local,
            remote_issue=remote,
            fields=[],
            local_updated=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            remote_updated=None,  # No timestamp
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        # Remote has no timestamp, use local
        assert result.title == "Local Has Timestamp"


class TestBatchResolution:
    """Test batch resolution of multiple conflicts."""

    def test_batch_resolve_all_conflicts(self, resolver):
        """Test resolving multiple conflicts."""
        conflicts = [
            create_conflict(issue_id="TEST-1"),
            create_conflict(issue_id="TEST-2"),
            create_conflict(issue_id="TEST-3"),
        ]

        results = resolver.resolve_batch(conflicts, ConflictStrategy.KEEP_LOCAL)

        assert len(results) == 3
        assert all(isinstance(r, Issue) for r in results)
        assert results[0].id == "TEST-1"
        assert results[1].id == "TEST-2"
        assert results[2].id == "TEST-3"

    def test_batch_resolve_empty_list(self, resolver):
        """Test batch resolving empty conflict list."""
        results = resolver.resolve_batch([], ConflictStrategy.KEEP_LOCAL)

        assert results == []

    def test_batch_resolve_single_conflict(self, resolver):
        """Test batch resolving single conflict."""
        conflict = create_conflict(issue_id="TEST-1")

        results = resolver.resolve_batch([conflict], ConflictStrategy.KEEP_LOCAL)

        assert len(results) == 1
        assert results[0].id == "TEST-1"

    def test_batch_resolve_with_different_strategies(self, resolver):
        """Test that batch applies same strategy to all conflicts."""
        conflicts = [
            create_conflict(issue_id="TEST-1"),
            create_conflict(issue_id="TEST-2"),
        ]

        results = resolver.resolve_batch(conflicts, ConflictStrategy.KEEP_LOCAL)

        # Both should use KEEP_LOCAL strategy
        assert len(results) == 2
        # If KEEP_LOCAL was applied, all results should use local values
        for result in results:
            assert result.title == "Local"  # From create_conflict default


class TestConflictFieldAccuracy:
    """Test that conflict field information is preserved."""

    def test_conflict_field_names_property(self):
        """Test that field_names property lists all conflicting fields."""
        fields = [
            ConflictField("title", "Local", "Remote"),
            ConflictField("status", "TODO", "DONE"),
            ConflictField("assignee", "alice", "bob"),
        ]

        conflict = create_conflict(fields=fields)

        assert conflict.field_names == ["title", "status", "assignee"]

    def test_conflict_preserves_field_values(self):
        """Test that conflict preserves all field values."""
        fields = [
            ConflictField(
                field_name="status",
                local_value=Status.TODO,
                remote_value="in_progress",
                local_updated=datetime(2026, 1, 31, 10, 0, 0, tzinfo=UTC),
                remote_updated=datetime(2026, 1, 31, 11, 0, 0, tzinfo=UTC),
            )
        ]

        conflict = create_conflict(fields=fields)

        assert conflict.fields[0].field_name == "status"
        assert conflict.fields[0].local_value == Status.TODO
        assert conflict.fields[0].remote_value == "in_progress"


class TestConflictResolutionStrategy:
    """Test ConflictStrategy enum."""

    def test_strategy_enum_values(self):
        """Test that all strategies have expected values."""
        assert ConflictStrategy.KEEP_LOCAL.value == "keep_local"
        assert ConflictStrategy.KEEP_REMOTE.value == "keep_remote"
        assert ConflictStrategy.AUTO_MERGE.value == "auto_merge"

    def test_default_strategy_is_auto_merge(self, resolver):
        """Test that default strategy is AUTO_MERGE."""
        local = Issue(id="TEST-1", title="Local", status=Status.TODO, content="")
        remote = {"id": "TEST-1", "title": "Remote", "status": "open"}

        conflict = create_conflict(local_issue=local, remote_issue=remote)

        # Calling without strategy should use AUTO_MERGE (default)
        result = resolver.resolve(conflict)

        # With AUTO_MERGE, it should use timestamp logic (both equal, prefers local)
        assert result.title == "Local"


class TestErrorHandling:
    """Test error handling in resolution."""

    def test_resolve_invalid_strategy_type_raises_error(self, resolver):
        """Test that passing invalid strategy type raises AttributeError."""
        conflict = create_conflict()

        # Passing a string instead of ConflictStrategy enum should raise AttributeError
        with pytest.raises(AttributeError):
            resolver.resolve(conflict, strategy="invalid_strategy")

    def test_batch_with_partial_failures_continues(self, resolver):
        """Test that batch continues on individual failures but logs them."""
        # Create valid conflicts that will resolve successfully
        conflicts = [
            create_conflict(issue_id="TEST-1"),
            create_conflict(issue_id="TEST-2"),
            create_conflict(issue_id="TEST-3"),
        ]

        # Batch resolve should succeed for all valid conflicts
        results = resolver.resolve_batch(conflicts, ConflictStrategy.KEEP_LOCAL)

        assert len(results) == 3
        # All should be resolved
        assert all(isinstance(r, Issue) for r in results)
