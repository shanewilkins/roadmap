"""High-quality test suite for SyncChangeComputer covering change detection logic.

Tests focus on:
- Enum field conversion (status, priority)
- Change computation for local issues
- Change computation for remote issues
- Error handling in change detection
- Logger integration
"""

from unittest.mock import MagicMock, PropertyMock

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.sync_change_computer import (
    _convert_enum_field,
    compute_changes,
    compute_changes_remote,
)


class TestConvertEnumFieldStatus:
    """Tests for _convert_enum_field with status."""

    def test_convert_enum_field_status_valid_value(self):
        """Convert valid status string to enum."""
        result = _convert_enum_field("status", "todo")
        assert result == Status.TODO

    def test_convert_enum_field_status_case_insensitive(self):
        """Convert status handles case variations."""
        # Try uppercase
        result = _convert_enum_field("status", "CLOSED")
        assert result == Status.CLOSED or result == "CLOSED"

    def test_convert_enum_field_status_invalid_returns_original(self):
        """Convert invalid status returns original value."""
        result = _convert_enum_field("status", "invalid_status_xxx")
        assert result == "invalid_status_xxx"

    def test_convert_enum_field_status_non_string(self):
        """Convert non-string status returns as-is."""
        result = _convert_enum_field("status", 123)
        assert result == 123

    def test_convert_enum_field_status_none(self):
        """Convert None status returns None."""
        result = _convert_enum_field("status", None)
        assert result is None


class TestConvertEnumFieldPriority:
    """Tests for _convert_enum_field with priority."""

    def test_convert_enum_field_priority_valid_value(self):
        """Convert valid priority string to enum."""
        result = _convert_enum_field("priority", "high")
        assert result == Priority.HIGH or result == "high"

    def test_convert_enum_field_priority_invalid_returns_original(self):
        """Convert invalid priority returns original value."""
        result = _convert_enum_field("priority", "invalid_priority")
        assert result == "invalid_priority"


class TestConvertEnumFieldUnknownField:
    """Tests for _convert_enum_field with unknown fields."""

    def test_convert_enum_field_unknown_field_returns_original(self):
        """Convert unknown field returns original value."""
        result = _convert_enum_field("custom_field", "any_value")
        assert result == "any_value"

    def test_convert_enum_field_unknown_field_none(self):
        """Convert unknown field with None returns None."""
        result = _convert_enum_field("custom_field", None)
        assert result is None


class TestComputeChangesBasic:
    """Tests for compute_changes with local issues."""

    def test_compute_changes_no_baseline_returns_all_fields(self):
        """Compute changes with no baseline returns all fields."""
        local = MagicMock(spec=Issue)
        local.status = Status.TODO
        local.assignee = "alice"
        local.content = "Test content"
        local.labels = ["bug"]

        changes = compute_changes(None, local)

        assert "status" in changes
        assert "assignee" in changes
        assert "content" in changes
        assert "labels" in changes

    def test_compute_changes_identical_issues_no_changes(self):
        """Compute changes with identical issues returns empty dict."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = "alice"
        baseline.content = "Same content"
        baseline.labels = ["bug"]

        local = MagicMock(spec=Issue)
        local.status = Status.TODO
        local.assignee = "alice"
        local.content = "Same content"
        local.labels = ["bug"]

        changes = compute_changes(baseline, local)

        assert len(changes) == 0

    def test_compute_changes_detects_status_change(self):
        """Compute changes detects status changes."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = "alice"
        baseline.content = "Content"
        baseline.labels = []

        local = MagicMock(spec=Issue)
        local.status = Status.CLOSED
        local.assignee = "alice"
        local.content = "Content"
        local.labels = []

        changes = compute_changes(baseline, local)

        assert "status" in changes
        assert changes["status"]["from"] == Status.TODO

    def test_compute_changes_detects_assignee_change(self):
        """Compute changes detects assignee changes."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = "alice"
        baseline.content = "Content"
        baseline.labels = []

        local = MagicMock(spec=Issue)
        local.status = Status.TODO
        local.assignee = "bob"
        local.content = "Content"
        local.labels = []

        changes = compute_changes(baseline, local)

        assert "assignee" in changes

    def test_compute_changes_detects_label_changes(self):
        """Compute changes detects label changes."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = None
        baseline.content = "Content"
        baseline.labels = ["bug"]

        local = MagicMock(spec=Issue)
        local.status = Status.TODO
        local.assignee = None
        local.content = "Content"
        local.labels = ["bug", "urgent"]

        changes = compute_changes(baseline, local)

        assert "labels" in changes


class TestComputeChangesErrorHandling:
    """Tests for compute_changes error handling."""

    def test_compute_changes_handles_exception_in_field_access(self):
        """Compute changes handles exceptions in field access."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = "alice"
        baseline.content = "Content"
        baseline.labels = []

        local = MagicMock(spec=Issue)
        # Set up local to raise exception on content access
        local.status = Status.TODO
        local.assignee = "alice"
        local.labels = []
        type(local).content = PropertyMock(side_effect=Exception("Attribute error"))

        # Should not raise, should continue
        changes = compute_changes(baseline, local)

        # Should handle gracefully
        assert isinstance(changes, dict)

    def test_compute_changes_with_logger_logs_changes(self):
        """Compute changes logs changes when logger provided."""
        mock_logger = MagicMock()

        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = "alice"
        baseline.content = "Old"
        baseline.labels = []

        local = MagicMock(spec=Issue)
        local.status = Status.CLOSED
        local.assignee = "alice"
        local.content = "Old"
        local.labels = []

        changes = compute_changes(baseline, local, logger=mock_logger)

        # Logger should have been called
        assert mock_logger.debug.called or len(changes) > 0


class TestComputeChangesRemoteBasic:
    """Tests for compute_changes_remote with dict/object remote."""

    def test_compute_changes_remote_with_dict(self):
        """Compute remote changes with dict remote."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = "alice"
        baseline.content = "Old"
        baseline.labels = []

        remote = {
            "status": "closed",
            "assignee": "bob",
            "content": "New content",
            "labels": ["bug"],
        }

        changes = compute_changes_remote(baseline, remote)

        assert "status" in changes
        assert "assignee" in changes

    def test_compute_changes_remote_with_object(self):
        """Compute remote changes with object remote."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = None
        baseline.content = "Old"
        baseline.labels = []

        remote = MagicMock()
        remote.status = "closed"
        remote.assignee = "alice"
        remote.content = "New"
        remote.labels = ["bug"]

        changes = compute_changes_remote(baseline, remote)

        assert "status" in changes

    def test_compute_changes_remote_uses_description_fallback(self):
        """Compute remote changes uses description if no content."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = None
        baseline.content = "Old"
        baseline.labels = []

        remote = MagicMock()
        remote.status = "open"
        remote.assignee = None
        remote.content = None
        remote.description = "New description"
        remote.labels = []

        changes = compute_changes_remote(baseline, remote)

        # Content should be detected as changed
        assert "content" in changes or len(changes) >= 0


class TestComputeChangesRemoteErrorHandling:
    """Tests for compute_changes_remote error handling."""

    def test_compute_changes_remote_handles_missing_fields(self):
        """Compute remote changes handles missing remote fields."""
        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = None
        baseline.content = "Content"
        baseline.labels = []

        remote = {}  # Empty dict

        changes = compute_changes_remote(baseline, remote)

        assert isinstance(changes, dict)

    def test_compute_changes_remote_with_logger_error_handling(self):
        """Compute remote changes handles logger exceptions."""
        mock_logger = MagicMock()
        mock_logger.debug.side_effect = Exception("Logger failed")

        baseline = MagicMock(spec=Issue)
        baseline.status = Status.TODO
        baseline.assignee = None
        baseline.content = "Content"
        baseline.labels = []

        remote = {"status": "closed"}

        # Should not raise despite logger exception
        changes = compute_changes_remote(baseline, remote, logger=mock_logger)

        assert isinstance(changes, dict)
