"""High-quality tests for ThreeWayMerger with state-transition validation.

Focus: Validates all 5 state transitions, reason field accuracy, edge cases.
Validates:
- All 5 merge cases: no change, only local, only remote, both same, both different
- Reason field explains exactly why decision was made
- Status (CLEAN/CONFLICT) is correct
- Merged value is exactly what's expected
- Edge cases: nulls, empty strings, type mismatches
- Parametrized scenarios for each state transition
"""

import pytest

from roadmap.core.services.sync.three_way_merger import (
    FieldMergeResult,
    MergeStatus,
    ThreeWayMerger,
)


class TestNoChangesCase:
    """Test Case 1: Neither side changed (base=local=remote)."""

    @pytest.mark.parametrize(
        "value",
        [
            "todo",
            "alice@example.com",
            "v1.0",
            "",  # Empty string
            None,  # None/null
            123,  # Numbers
            True,  # Booleans
            ["bug", "feature"],  # Lists
        ],
    )
    def test_no_changes_returns_clean(self, value):
        """Test that unchanged field returns CLEAN status."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            field_name="status",
            base=value,
            local=value,
            remote=value,
        )

        assert result.status == MergeStatus.CLEAN, f"Should be CLEAN for {value}"
        assert result.value == value, f"Should return the value: {value}"
        assert result.is_conflict() is False
        assert "no changes" in result.reason

    def test_no_changes_reason_field(self):
        """Test that reason field explains no changes occurred."""
        merger = ThreeWayMerger()

        result = merger.merge_field("title", base="Test", local="Test", remote="Test")

        assert "no changes" in result.reason
        assert "title" in result.reason


class TestOnlyLocalChangedCase:
    """Test Case 2: Only local changed (base≠local, remote=base)."""

    @pytest.mark.parametrize(
        "base,local",
        [
            ("todo", "in-progress"),
            (None, "assigned"),
            ("old", "new"),
            ([], ["item"]),
            ("", "something"),
        ],
    )
    def test_only_local_changed_returns_clean_local(self, base, local):
        """Test that only-local changes return CLEAN with local value."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            field_name="status",
            base=base,
            local=local,
            remote=base,  # Remote stays at base
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == local, f"Should use local value: {local}"
        assert result.is_conflict() is False
        assert "only local changed" in result.reason

    def test_only_local_changed_reason_includes_field_name(self):
        """Test that reason includes field name."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "assignee", base="alice", local="bob", remote="alice"
        )

        assert "assignee" in result.reason
        assert "only local changed" in result.reason


class TestOnlyRemoteChangedCase:
    """Test Case 3: Only remote changed (base≠remote, local=base)."""

    @pytest.mark.parametrize(
        "base,remote",
        [
            ("todo", "closed"),
            ("alice", None),
            ("v1.0", "v2.0"),
            ([], ["tag"]),
            ("", "filled"),
        ],
    )
    def test_only_remote_changed_returns_clean_remote(self, base, remote):
        """Test that only-remote changes return CLEAN with remote value."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            field_name="milestone",
            base=base,
            local=base,  # Local stays at base
            remote=remote,
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == remote, f"Should use remote value: {remote}"
        assert result.is_conflict() is False
        assert "only remote changed" in result.reason

    def test_only_remote_changed_reason_includes_field_name(self):
        """Test that reason includes field name."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "status", base="open", local="open", remote="closed"
        )

        assert "status" in result.reason
        assert "only remote changed" in result.reason


class TestBothChangedSameCase:
    """Test Case 4: Both changed to same value (local=remote≠base)."""

    @pytest.mark.parametrize(
        "base,both",
        [
            ("todo", "in-progress"),
            (None, "assigned"),
            ("v1.0", "v2.0"),
            ([], ["tag"]),
            (0, 1),
        ],
    )
    def test_both_changed_same_returns_clean(self, base, both):
        """Test that both sides changing to same value returns CLEAN."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            field_name="status",
            base=base,
            local=both,
            remote=both,
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == both
        assert result.is_conflict() is False
        assert "both changed to same value" in result.reason

    def test_both_changed_same_reason_includes_field_name(self):
        """Test that reason includes field name."""
        merger = ThreeWayMerger()

        result = merger.merge_field("assignee", base="alice", local="bob", remote="bob")

        assert "assignee" in result.reason
        assert "both changed to same value" in result.reason


class TestBothChangedDifferentlyCase:
    """Test Case 5: Both changed differently (local≠remote, both≠base) - TRUE CONFLICT."""

    @pytest.mark.parametrize(
        "base,local,remote",
        [
            ("todo", "in-progress", "closed"),
            ("alice", "bob", "charlie"),
            ("v1.0", "v2.0", "v1.5"),
            (None, "local", "remote"),
            ("base", None, "remote"),
        ],
    )
    def test_both_changed_differently_returns_conflict(self, base, local, remote):
        """Test that both sides changing differently returns CONFLICT."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            field_name="status",
            base=base,
            local=local,
            remote=remote,
        )

        assert result.status == MergeStatus.CONFLICT
        assert result.value is None, "Conflict should have None value"
        assert result.is_conflict() is True
        assert "both sides changed differently" in result.reason

    def test_conflict_reason_includes_all_three_values(self):
        """Test that conflict reason shows all three values for debugging."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            field_name="status",
            base="todo",
            local="in-progress",
            remote="closed",
        )

        assert "base=todo" in result.reason
        assert "local=in-progress" in result.reason
        assert "remote=closed" in result.reason

    def test_conflict_reason_includes_field_name(self):
        """Test that conflict reason includes field name."""
        merger = ThreeWayMerger()

        result = merger.merge_field("milestone", base="v1", local="v2", remote="v3")

        assert "milestone" in result.reason


class TestEdgeCases:
    """Test edge cases: nulls, empty values, type mismatches."""

    def test_merge_with_all_nulls(self):
        """Test merging when all three are None."""
        merger = ThreeWayMerger()

        result = merger.merge_field("field", base=None, local=None, remote=None)

        assert result.status == MergeStatus.CLEAN
        assert result.value is None
        assert "no changes" in result.reason

    def test_merge_null_to_value(self):
        """Test merging from None (base) to value (only local changed)."""
        merger = ThreeWayMerger()

        result = merger.merge_field("field", base=None, local="assigned", remote=None)

        assert result.status == MergeStatus.CLEAN
        assert result.value == "assigned"
        assert "only local changed" in result.reason

    def test_merge_value_to_null(self):
        """Test merging from value to None (only remote changed)."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "field", base="assigned", local="assigned", remote=None
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value is None
        assert "only remote changed" in result.reason

    def test_merge_empty_string_vs_none(self):
        """Test that empty string and None are treated as different."""
        merger = ThreeWayMerger()

        result = merger.merge_field("field", base=None, local="", remote=None)

        # Empty string != None, so it's a change
        assert result.status == MergeStatus.CLEAN
        assert result.value == ""
        assert "only local changed" in result.reason

    def test_merge_empty_list_vs_none(self):
        """Test that empty list and None are treated as different."""
        merger = ThreeWayMerger()

        result = merger.merge_field("labels", base=None, local=[], remote=None)

        assert result.status == MergeStatus.CLEAN
        assert result.value == []

    def test_merge_lists(self):
        """Test merging list values (both changed to same list)."""
        merger = ThreeWayMerger()

        labels = ["bug", "urgent"]
        result = merger.merge_field(
            "labels",
            base=["bug"],
            local=labels,
            remote=labels,
        )

        assert result.status == MergeStatus.CLEAN
        assert result.value == labels
        assert "both changed to same value" in result.reason

    def test_merge_different_list_types_is_conflict(self):
        """Test that different list values cause conflict."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "labels",
            base=["bug"],
            local=["bug", "urgent"],
            remote=["bug", "feature"],
        )

        assert result.status == MergeStatus.CONFLICT
        assert result.value is None

    def test_merge_type_mismatch_is_conflict(self):
        """Test that type mismatches cause conflict."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "field",
            base="123",
            local=123,
            remote=456,
        )

        # 123 != 456, and both != "123", so it's a conflict
        assert result.status == MergeStatus.CONFLICT

    def test_merge_boolean_values(self):
        """Test merging boolean values."""
        merger = ThreeWayMerger()

        result = merger.merge_field("done", base=False, local=True, remote=False)

        assert result.status == MergeStatus.CLEAN
        assert result.value is True
        assert "only local changed" in result.reason

    def test_merge_numeric_values(self):
        """Test merging numeric values."""
        merger = ThreeWayMerger()

        result = merger.merge_field("count", base=0, local=5, remote=0)

        assert result.status == MergeStatus.CLEAN
        assert result.value == 5
        assert "only local changed" in result.reason


class TestMergeStatusEnum:
    """Test MergeStatus enum and FieldMergeResult."""

    def test_merge_status_values(self):
        """Test that MergeStatus has expected values."""
        assert MergeStatus.CLEAN.value == "clean"
        assert MergeStatus.CONFLICT.value == "conflict"

    def test_field_merge_result_is_conflict_method(self):
        """Test is_conflict() method."""
        clean = FieldMergeResult("value", MergeStatus.CLEAN, "no changes")
        conflict = FieldMergeResult(None, MergeStatus.CONFLICT, "conflict")

        assert clean.is_conflict() is False
        assert conflict.is_conflict() is True

    def test_field_merge_result_dataclass_fields(self):
        """Test that FieldMergeResult has expected fields."""
        result = FieldMergeResult("resolved", MergeStatus.CLEAN, "explanation")

        assert result.value == "resolved"
        assert result.status == MergeStatus.CLEAN
        assert result.reason == "explanation"


class TestReasonFieldAccuracy:
    """Test that reason field accurately describes the merge decision."""

    def test_reason_for_no_change_is_accurate(self):
        """Test reason describes no-change scenario."""
        merger = ThreeWayMerger()

        result = merger.merge_field("title", base="Test", local="Test", remote="Test")

        assert "title" in result.reason
        assert "no changes" in result.reason

    def test_reason_for_local_only_is_accurate(self):
        """Test reason describes local-only change."""
        merger = ThreeWayMerger()

        result = merger.merge_field("title", base="Old", local="New", remote="Old")

        assert "title" in result.reason
        assert "only local changed" in result.reason

    def test_reason_for_remote_only_is_accurate(self):
        """Test reason describes remote-only change."""
        merger = ThreeWayMerger()

        result = merger.merge_field("title", base="Old", local="Old", remote="New")

        assert "title" in result.reason
        assert "only remote changed" in result.reason

    def test_reason_for_both_same_is_accurate(self):
        """Test reason describes both-sides same scenario."""
        merger = ThreeWayMerger()

        result = merger.merge_field("title", base="Old", local="New", remote="New")

        assert "title" in result.reason
        assert "both changed to same value" in result.reason

    def test_reason_for_conflict_is_detailed(self):
        """Test reason for conflict includes diagnostic info."""
        merger = ThreeWayMerger()

        result = merger.merge_field(
            "status",
            base="todo",
            local="in-progress",
            remote="closed",
        )

        # Should include all three values for debugging
        assert "todo" in result.reason
        assert "in-progress" in result.reason
        assert "closed" in result.reason
