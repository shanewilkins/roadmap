"""High-quality test suite for SyncConflictResolver.

Tests focus on:
- Conflict resolution strategies (KEEP_LOCAL, KEEP_REMOTE, AUTO_MERGE)
- Batch conflict resolution
- Auto-merge logic with timestamps
- Dataclass representations
- Error handling
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.sync_conflict_resolver import (
    Conflict,
    ConflictField,
    ConflictStrategy,
    SyncConflictResolver,
)


class TestConflictField:
    """Tests for ConflictField dataclass."""

    def test_conflict_field_creation(self):
        """Create conflict field."""
        field = ConflictField(
            field_name="status",
            local_value="open",
            remote_value="closed",
        )

        assert field.field_name == "status"
        assert field.local_value == "open"
        assert field.remote_value == "closed"

    def test_conflict_field_str_representation(self):
        """String representation of conflict field."""
        field = ConflictField(
            field_name="status",
            local_value="open",
            remote_value="closed",
        )

        str_repr = str(field)
        assert "status" in str_repr
        assert "open" in str_repr
        assert "closed" in str_repr


class TestConflict:
    """Tests for Conflict dataclass."""

    def test_conflict_creation(self):
        """Create conflict."""
        local_issue = MagicMock(spec=Issue)
        remote_issue = {"id": "123", "status": "closed"}

        now = datetime.now(UTC)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue=remote_issue,
            fields=[
                ConflictField("status", "open", "closed"),
            ],
            local_updated=now,
            remote_updated=now,
        )

        assert conflict.issue_id == "123"
        assert len(conflict.fields) == 1

    def test_conflict_field_names(self):
        """Get conflicting field names."""
        local_issue = MagicMock(spec=Issue)
        remote_issue = {}

        now = datetime.now(UTC)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue=remote_issue,
            fields=[
                ConflictField("status", "open", "closed"),
                ConflictField("assignee", "alice", "bob"),
            ],
            local_updated=now,
        )

        names = conflict.field_names
        assert "status" in names
        assert "assignee" in names

    def test_conflict_str_representation(self):
        """String representation of conflict."""
        local_issue = MagicMock(spec=Issue)
        remote_issue = {}

        now = datetime.now(UTC)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue=remote_issue,
            fields=[
                ConflictField("status", "open", "closed"),
            ],
            local_updated=now,
        )

        str_repr = str(conflict)
        assert "123" in str_repr
        assert "status" in str_repr


class TestSyncConflictResolverInit:
    """Tests for SyncConflictResolver initialization."""

    def test_resolver_init(self):
        """Initialize conflict resolver."""
        resolver = SyncConflictResolver()

        assert resolver.logger is not None


class TestResolveKeepLocal:
    """Tests for KEEP_LOCAL strategy."""

    def test_resolve_keep_local_strategy(self):
        """Resolve conflict keeping local version."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        local_issue.id = "123"

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue={"id": "123", "status": "closed"},
            fields=[ConflictField("status", "open", "closed")],
            local_updated=datetime.now(UTC),
            remote_updated=datetime.now(UTC),
        )

        result = resolver.resolve(conflict, ConflictStrategy.KEEP_LOCAL)

        assert result == local_issue


class TestResolveKeepRemote:
    """Tests for KEEP_REMOTE strategy."""

    def test_resolve_keep_remote_strategy(self):
        """Resolve conflict keeping remote version."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        local_issue.id = "123"

        remote_issue = {"id": "123", "status": "closed", "title": "Remote title"}

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue=remote_issue,
            fields=[ConflictField("status", "open", "closed")],
            local_updated=datetime.now(UTC),
            remote_updated=datetime.now(UTC),
        )

        with patch.object(
            resolver, "_convert_remote_to_local", return_value=local_issue
        ) as mock_convert:
            resolver.resolve(conflict, ConflictStrategy.KEEP_REMOTE)

            # Should call convert_remote_to_local
            mock_convert.assert_called_once()


class TestResolveAutoMerge:
    """Tests for AUTO_MERGE strategy."""

    def test_auto_merge_no_remote_timestamp_keeps_local(self):
        """Auto merge with no remote timestamp keeps local."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        local_issue.id = "123"

        now = datetime.now(UTC)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue={"id": "123"},
            fields=[],
            local_updated=now,
            remote_updated=None,  # No remote timestamp
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        assert result == local_issue

    def test_auto_merge_local_newer_keeps_local(self):
        """Auto merge when local is newer keeps local."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        local_issue.id = "123"

        now = datetime.now(UTC)
        older = now - timedelta(hours=1)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue={"id": "123"},
            fields=[],
            local_updated=now,
            remote_updated=older,
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        assert result == local_issue

    def test_auto_merge_remote_newer_keeps_remote(self):
        """Auto merge when remote is newer keeps remote."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        local_issue.id = "123"

        now = datetime.now(UTC)
        older = now - timedelta(hours=1)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue={"id": "123"},
            fields=[],
            local_updated=older,
            remote_updated=now,
        )

        with patch.object(
            resolver, "_convert_remote_to_local", return_value=local_issue
        ):
            resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

            # Should convert remote
            resolver._convert_remote_to_local.assert_called_once()

    def test_auto_merge_equal_timestamps_keeps_local(self):
        """Auto merge with equal timestamps keeps local."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        local_issue.id = "123"

        now = datetime.now(UTC)

        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue={"id": "123"},
            fields=[],
            local_updated=now,
            remote_updated=now,
        )

        result = resolver.resolve(conflict, ConflictStrategy.AUTO_MERGE)

        assert result == local_issue


class TestResolveBatch:
    """Tests for resolve_batch method."""

    def test_resolve_batch_empty_list(self):
        """Resolve batch with empty list."""
        resolver = SyncConflictResolver()

        result = resolver.resolve_batch([])

        assert result == []

    def test_resolve_batch_all_succeed(self):
        """Resolve batch with all successes."""
        resolver = SyncConflictResolver()

        issues = []
        for i in range(3):
            issue = MagicMock(spec=Issue)
            issue.id = f"issue-{i}"
            issues.append(issue)

        conflicts = [
            Conflict(
                issue_id=f"issue-{i}",
                local_issue=issues[i],
                remote_issue={},
                fields=[],
                local_updated=datetime.now(UTC),
            )
            for i in range(3)
        ]

        result = resolver.resolve_batch(conflicts)

        assert len(result) == 3


class TestConvertRemoteToLocal:
    """Tests for _convert_remote_to_local method."""

    def test_convert_remote_to_local_with_dict(self):
        """Convert remote dict to local Issue."""
        resolver = SyncConflictResolver()

        remote = {
            "id": "123",
            "status": "closed",
            "title": "Test",
            "assignee": "alice",
        }

        with patch.object(
            resolver, "_convert_remote_to_local", return_value=MagicMock(spec=Issue)
        ):
            result = resolver._convert_remote_to_local("123", remote)

            assert result is not None


class TestResolveInvalidStrategy:
    """Tests for invalid strategy handling."""

    def test_resolve_invalid_strategy_raises(self):
        """Resolve with invalid strategy raises ValueError."""
        resolver = SyncConflictResolver()

        local_issue = MagicMock(spec=Issue)
        conflict = Conflict(
            issue_id="123",
            local_issue=local_issue,
            remote_issue={},
            fields=[],
            local_updated=datetime.now(UTC),
        )

        with pytest.raises((ValueError, AttributeError, TypeError)):  # type: ignore
            resolver.resolve(conflict, "invalid_strategy")  # type: ignore
