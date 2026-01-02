"""Tests for ThreeWayMerger."""

from roadmap.core.services.sync.three_way_merger import (
    FieldMergeResult,
    MergeStatus,
    ThreeWayMerger,
)


class TestThreeWayMerger:
    """Test three-way merge logic."""

    def test_no_changes(self):
        """Test when neither local nor remote changed."""
        merger = ThreeWayMerger()

        result = merger.merge_field("status", "todo", "todo", "todo")

        assert result.status == MergeStatus.CLEAN
        assert result.value == "todo"
        assert "no changes" in result.reason

    def test_only_local_changed(self):
        """Test when only local changed."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "status", base="todo", local="in-progress", remote="todo"
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == "in-progress"
        assert "only local changed" in result.reason

    def test_only_remote_changed(self):
        """Test when only remote changed."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "status", base="todo", local="todo", remote="closed"
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == "closed"
        assert "only remote changed" in result.reason

    def test_both_changed_same_way(self):
        """Test when both sides made the same change."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "status", base="todo", local="in-progress", remote="in-progress"
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == "in-progress"
        assert "same value" in result.reason

    def test_both_changed_differently(self):
        """Test when both sides changed differently - TRUE CONFLICT."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "status", base="todo", local="in-progress", remote="closed"
        )

        assert result.status == MergeStatus.CONFLICT
        assert result.value is None
        assert "both sides changed differently" in result.reason

    def test_merge_issue_with_no_conflicts(self):
        """Test merging an issue with no conflicts."""
        merger = ThreeWayMerger()

        base = {
            "status": "todo",
            "assignee": None,
            "description": "Fix bug",
        }
        local = {
            "status": "in-progress",
            "assignee": "alice",
            "description": "Fix bug",
        }
        remote = {
            "status": "todo",
            "assignee": None,
            "description": "Fix bug - urgent",
        }

        merged, conflicts = merger.merge_issue("issue-1", base, local, remote)

        assert len(conflicts) == 0
        assert merged["status"] == "in-progress"  # Only local changed
        assert merged["description"] == "Fix bug - urgent"  # Only remote changed
        assert merged["assignee"] == "alice"  # Only local changed

    def test_merge_issue_with_conflicts(self):
        """Test merging an issue with conflicts."""
        merger = ThreeWayMerger()

        base = {"status": "todo", "assignee": None}
        local = {"status": "in-progress", "assignee": "alice"}
        remote = {"status": "closed", "assignee": "bob"}

        merged, conflicts = merger.merge_issue("issue-2", base, local, remote)

        assert "status" in conflicts
        assert "assignee" in conflicts
        assert len(conflicts) == 2
        # Conflicted fields should not be in merged
        assert "status" not in merged
        assert "assignee" not in merged

    def test_merge_issue_partial_conflicts(self):
        """Test merging with some conflicts and some clean merges."""
        merger = ThreeWayMerger()

        base = {
            "status": "todo",
            "assignee": None,
            "labels": ["bug"],
            "description": "Original",
        }
        local = {
            "status": "in-progress",  # Changed locally
            "assignee": None,  # Unchanged
            "labels": ["bug", "urgent"],  # Changed locally
            "description": "Original",  # Unchanged
        }
        remote = {
            "status": "closed",  # Changed remotely
            "assignee": "alice",  # Changed remotely
            "labels": ["bug"],  # Unchanged
            "description": "Updated description",  # Changed remotely
        }

        merged, conflicts = merger.merge_issue("issue-3", base, local, remote)

        # Status: both changed → conflict
        assert "status" in conflicts
        # Assignee: only remote changed → merged
        assert merged["assignee"] == "alice"
        # Labels: only local changed → merged
        assert merged["labels"] == ["bug", "urgent"]
        # Description: only remote changed → merged
        assert merged["description"] == "Updated description"

    def test_merge_issues_with_multiple_issues(self):
        """Test merging multiple issues."""
        merger = ThreeWayMerger()

        base_issues = {
            "issue-1": {"status": "todo"},
            "issue-2": {"status": "todo"},
        }
        local_issues = {
            "issue-1": {"status": "in-progress"},
            "issue-2": {"status": "todo"},
        }
        remote_issues = {
            "issue-1": {"status": "in-progress"},
            "issue-2": {"status": "closed"},
        }

        results, deleted = merger.merge_issues(
            {}, base_issues, local_issues, remote_issues
        )

        assert len(results) == 2
        # issue-1: both changed same way → clean
        assert results["issue-1"][0]["status"] == "in-progress"
        assert len(results["issue-1"][1]) == 0  # No conflicts
        # issue-2: only remote changed → clean
        assert results["issue-2"][0]["status"] == "closed"
        assert len(results["issue-2"][1]) == 0  # No conflicts

    def test_merge_issues_deleted_remotely(self):
        """Test handling of issues deleted on remote."""
        merger = ThreeWayMerger()

        base_issues = {
            "issue-1": {"status": "todo"},
            "issue-2": {"status": "closed"},
        }
        local_issues = {
            "issue-1": {"status": "in-progress"},
            # issue-2 is NOT in local (not modified, so can be safely deleted)
        }
        remote_issues = {
            "issue-1": {"status": "in-progress"},
            # issue-2 is gone from remote
        }

        results, deleted = merger.merge_issues(
            {}, base_issues, local_issues, remote_issues
        )

        # issue-2 should be in deleted (deleted remotely, not in local)
        assert "issue-2" in deleted
        assert "issue-1" not in deleted


class TestFieldMergeResult:
    """Test FieldMergeResult."""

    def test_is_conflict(self):
        """Test is_conflict method."""
        clean = FieldMergeResult("value", MergeStatus.CLEAN, "no conflict")
        conflict = FieldMergeResult(None, MergeStatus.CONFLICT, "conflict")

        assert not clean.is_conflict()
        assert conflict.is_conflict()


class TestEdgeCases:
    """Test edge cases."""

    def test_none_values(self):
        """Test merging with None values."""
        merger = ThreeWayMerger()

        # None → assigned
        result = merger.merge_field("assignee", None, "alice", None)
        assert result.status == MergeStatus.CLEAN
        assert result.value == "alice"

        # assigned → None
        result = merger.merge_field("assignee", "alice", None, "alice")
        assert result.status == MergeStatus.CLEAN
        assert result.value is None

    def test_empty_strings(self):
        """Test merging with empty strings."""
        merger = ThreeWayMerger()

        result = merger.merge_field("description", "", "Fix", "")
        assert result.status == MergeStatus.CLEAN
        assert result.value == "Fix"

    def test_numeric_values(self):
        """Test merging numeric values."""
        merger = ThreeWayMerger()

        result = merger.merge_field("priority", 1, 2, 1)
        assert result.status == MergeStatus.CLEAN
        assert result.value == 2
