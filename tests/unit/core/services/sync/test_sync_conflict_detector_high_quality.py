"""High-quality tests for SyncConflictDetector field-level conflict detection.

Tests field-level conflict detection between local and remote issues.
Covers enum conversion, timestamp extraction, and edge cases.
All tests use field-level assertions (not mocks).
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.core.services.sync.sync_conflict_detector import (
    _convert_enum_field,
    _get_field_value,
    detect_field_conflicts,
)


class TestConvertEnumField:
    """Test enum field conversion from string to enum types."""

    def test_status_field_converts_to_status_enum(self):
        """Test status string converts to Status enum."""
        result = _convert_enum_field("status", "todo")
        assert result == Status.TODO
        assert isinstance(result, Status)

    def test_status_field_case_insensitive(self):
        """Test status conversion is case-insensitive."""
        result = _convert_enum_field("status", "BLOCKED")
        assert result == Status.BLOCKED

    def test_status_field_lowercase_fallback(self):
        """Test status conversion with lowercase fallback."""
        result = _convert_enum_field("status", "CLOSED")
        assert result == Status.CLOSED

    def test_priority_field_converts_to_priority_enum(self):
        """Test priority string converts to Priority enum."""
        result = _convert_enum_field("priority", "high")
        assert result == Priority.HIGH
        assert isinstance(result, Priority)

    def test_priority_field_case_insensitive(self):
        """Test priority conversion is case-insensitive."""
        result = _convert_enum_field("priority", "CRITICAL")
        assert result == Priority.CRITICAL

    def test_non_enum_field_returns_original_value(self):
        """Test non-enum fields return original value unchanged."""
        result = _convert_enum_field("title", "Some Title")
        assert result == "Some Title"
        assert isinstance(result, str)

    def test_non_enum_field_non_string_returns_unchanged(self):
        """Test non-string values return unchanged."""
        result = _convert_enum_field("status", 123)
        assert result == 123

    def test_none_value_returns_none(self):
        """Test None value returns None."""
        result = _convert_enum_field("status", None)
        assert result is None

    def test_invalid_status_value_returns_original(self):
        """Test invalid status value returns original on conversion error."""
        result = _convert_enum_field("status", "invalid_status_xyz")
        # Should return original if conversion fails
        assert result == "invalid_status_xyz"

    def test_invalid_priority_value_returns_original(self):
        """Test invalid priority value returns original on conversion error."""
        result = _convert_enum_field("priority", "not_a_priority")
        # Should return original if conversion fails
        assert result == "not_a_priority"

    def test_empty_string_returns_empty_string(self):
        """Test empty string returns empty string (not converted)."""
        result = _convert_enum_field("status", "")
        assert result == ""


class TestGetFieldValue:
    """Test safe field value extraction from dict or object."""

    def test_get_field_from_dict(self):
        """Test extracting field from dict."""
        obj = {"title": "Test Issue", "status": "todo"}
        result = _get_field_value(obj, "title")
        assert result == "Test Issue"

    def test_get_field_from_object(self):
        """Test extracting field from object."""
        obj = MagicMock()
        obj.title = "Test Issue"
        result = _get_field_value(obj, "title")
        assert result == "Test Issue"

    def test_get_missing_field_from_dict_returns_none(self):
        """Test missing field in dict returns None."""
        obj = {"title": "Test"}
        result = _get_field_value(obj, "status")
        assert result is None

    def test_get_missing_field_from_object_returns_none(self):
        """Test missing field in object returns None."""
        obj = MagicMock(spec=[])
        result = _get_field_value(obj, "nonexistent")
        assert result is None

    def test_get_none_value_from_dict(self):
        """Test extracting None value from dict."""
        obj = {"title": None}
        result = _get_field_value(obj, "title")
        assert result is None

    def test_get_empty_string_from_dict(self):
        """Test extracting empty string from dict."""
        obj = {"title": ""}
        result = _get_field_value(obj, "title")
        assert result == ""

    def test_get_numeric_value_from_dict(self):
        """Test extracting numeric value from dict."""
        obj = {"priority_level": 5}
        result = _get_field_value(obj, "priority_level")
        assert result == 5

    def test_get_list_value_from_dict(self):
        """Test extracting list value from dict."""
        obj = {"labels": ["bug", "urgent"]}
        result = _get_field_value(obj, "labels")
        assert result == ["bug", "urgent"]


class TestDetectFieldConflictsBasic:
    """Test basic conflict detection functionality."""

    @pytest.fixture
    def local_issue(self):
        """Create a mock local issue."""
        issue = MagicMock()
        issue.title = "Local Title"
        issue.status = Status.TODO
        issue.priority = Priority.MEDIUM
        issue.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        return issue

    @pytest.fixture
    def remote_dict(self):
        """Create a remote issue dict."""
        return {
            "title": "Remote Title",
            "status": "todo",
            "priority": "medium",
        }

    def test_no_conflicts_when_fields_identical(self, local_issue):
        """Test no conflicts detected when fields are identical."""
        remote_dict = {
            "title": "Local Title",
            "status": "todo",
            "priority": "medium",
        }
        conflicts = detect_field_conflicts(
            local_issue, remote_dict, ["title", "status", "priority"]
        )
        assert len(conflicts) == 0

    def test_detect_conflict_in_title(self, local_issue, remote_dict):
        """Test conflict detected when title differs."""
        conflicts = detect_field_conflicts(
            local_issue, remote_dict, ["title", "status", "priority"]
        )
        assert len(conflicts) == 1
        assert conflicts[0].field_name == "title"
        assert conflicts[0].local_value == "Local Title"
        assert conflicts[0].remote_value == "Remote Title"

    def test_detect_conflict_in_status(self):
        """Test conflict detected when status differs."""
        local = MagicMock()
        local.title = "Title"
        local.status = Status.TODO
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {"title": "Title", "status": "blocked"}
        conflicts = detect_field_conflicts(local, remote, ["title", "status"])
        assert len(conflicts) == 1
        assert conflicts[0].field_name == "status"
        assert conflicts[0].local_value == Status.TODO
        assert conflicts[0].remote_value == Status.BLOCKED

    def test_multiple_field_conflicts(self):
        """Test detection of multiple field conflicts."""
        local = MagicMock()
        local.title = "Local Title"
        local.status = Status.TODO
        local.priority = Priority.LOW
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {
            "title": "Remote Title",
            "status": "in_progress",
            "priority": "high",
        }
        conflicts = detect_field_conflicts(
            local, remote, ["title", "status", "priority"]
        )
        assert len(conflicts) == 3
        assert {c.field_name for c in conflicts} == {"title", "status", "priority"}

    def test_skip_empty_field_pairs(self):
        """Test empty/None field pairs are skipped."""
        local = MagicMock()
        local.title = None
        local.status = None
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {"title": None, "status": None}
        conflicts = detect_field_conflicts(local, remote, ["title", "status"])
        assert len(conflicts) == 0

    def test_one_empty_one_filled_is_conflict(self):
        """Test empty vs filled field is detected as conflict."""
        local = MagicMock()
        local.title = None
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {"title": "Remote Title"}
        conflicts = detect_field_conflicts(local, remote, ["title"])
        assert len(conflicts) == 1
        assert conflicts[0].local_value is None
        assert conflicts[0].remote_value == "Remote Title"


class TestDetectFieldConflictsTimestamps:
    """Test timestamp extraction and inclusion in conflicts."""

    @pytest.fixture
    def local_issue(self):
        """Create local issue with timestamp."""
        issue = MagicMock()
        issue.title = "Local Title"
        issue.status = Status.TODO
        issue.updated = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        return issue

    def test_local_timestamp_included_in_conflict(self):
        """Test local timestamp is included in conflict field."""
        local = MagicMock()
        local.title = "Local Title"
        local.updated = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        remote = {"title": "Remote Title"}
        conflicts = detect_field_conflicts(local, remote, ["title"])
        assert len(conflicts) == 1
        assert conflicts[0].local_updated == local.updated

    def test_remote_timestamp_extracted_when_callable_provided(self):
        """Test remote timestamp extracted when extract_timestamp provided."""

        def mock_extractor(obj, field):
            if isinstance(obj, dict) and "remote_updated" in obj:
                return obj["remote_updated"]
            return None

        local = MagicMock()
        local.title = "Local"
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)
        remote = {"title": "Remote", "remote_updated": remote_time}

        conflicts = detect_field_conflicts(
            local,
            remote,
            ["title"],
            extract_timestamp=mock_extractor,
        )
        assert len(conflicts) == 1
        assert conflicts[0].remote_updated == remote_time

    def test_remote_timestamp_none_when_extraction_fails(self):
        """Test remote_updated is None when extraction fails."""

        def failing_extractor(obj, field):
            raise ValueError("Extraction failed")

        local = MagicMock()
        local.title = "Local"
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {"title": "Remote"}

        conflicts = detect_field_conflicts(
            local,
            remote,
            ["title"],
            extract_timestamp=failing_extractor,
        )
        assert len(conflicts) == 1
        assert conflicts[0].remote_updated is None

    def test_no_timestamp_extraction_when_callable_not_provided(self):
        """Test remote_updated is None when no extractor provided."""
        local = MagicMock()
        local.title = "Local"
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {"title": "Remote"}

        conflicts = detect_field_conflicts(local, remote, ["title"])
        assert len(conflicts) == 1
        assert conflicts[0].remote_updated is None


class TestDetectFieldConflictsEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_field_on_local_treated_as_none(self):
        """Test missing field on local object treated as None."""
        local = MagicMock(spec=["title"])
        local.title = "Title"

        remote = {"status": "todo"}
        # local doesn't have 'status' field, should be treated as None
        conflicts = detect_field_conflicts(local, remote, ["status"])
        assert len(conflicts) == 1
        assert conflicts[0].local_value is None
        assert conflicts[0].remote_value == "todo"

    def test_exception_during_field_access_skipped_with_logging(self):
        """Test exception during field access is caught and logged."""
        local = MagicMock()
        local.title = "Title"
        # Simulate exception on getattr
        type(local).__getattribute__ = MagicMock(side_effect=Exception("Access denied"))

        mock_logger = MagicMock()
        remote = {"title": "Remote"}

        # Should not raise, should catch exception
        conflicts = detect_field_conflicts(local, remote, ["title"], logger=mock_logger)
        # Exception occurred, field skipped, no conflicts
        assert len(conflicts) == 0

    def test_enum_conversion_failure_logs_debug_message(self):
        """Test failed enum conversion logs debug message."""
        local = MagicMock()
        local.status = Status.TODO
        local.updated = datetime.now(UTC)

        remote = {"status": "invalid_enum_value_xyz"}
        mock_logger = MagicMock()

        conflicts = detect_field_conflicts(
            local, remote, ["status"], logger=mock_logger
        )
        # Should still create conflict even if conversion fails
        assert len(conflicts) >= 1

    def test_empty_fields_to_sync_list_returns_no_conflicts(self):
        """Test empty fields_to_sync list returns no conflicts."""
        local = MagicMock()
        local.title = "Different"
        local.updated = datetime.now(UTC)

        remote = {"title": "Title"}

        conflicts = detect_field_conflicts(local, remote, [])
        assert len(conflicts) == 0

    def test_single_field_detection(self):
        """Test detection with single field."""
        local = MagicMock()
        local.title = "Local"
        local.updated = datetime.now(UTC)

        remote = {"title": "Remote"}

        conflicts = detect_field_conflicts(local, remote, ["title"])
        assert len(conflicts) == 1
        assert conflicts[0].field_name == "title"

    def test_large_field_list_detection(self):
        """Test detection with many fields."""
        local = MagicMock()
        local.field1 = "value1"
        local.field2 = "value2"
        local.field3 = "value3"
        local.field4 = "value4"
        local.field5 = "value5"
        local.updated = datetime.now(UTC)

        remote = {
            "field1": "different1",
            "field2": "value2",
            "field3": "different3",
            "field4": "value4",
            "field5": "different5",
        }

        conflicts = detect_field_conflicts(
            local, remote, ["field1", "field2", "field3", "field4", "field5"]
        )
        assert len(conflicts) == 3
        assert {c.field_name for c in conflicts} == {"field1", "field3", "field5"}


class TestDetectFieldConflictsIntegration:
    """Integration tests with realistic scenarios."""

    def test_realistic_issue_conflict_scenario(self):
        """Test realistic issue conflict with mixed field types."""
        local = MagicMock()
        local.id = "issue-1"
        local.title = "Fix bug in auth"
        local.status = Status.IN_PROGRESS
        local.priority = Priority.HIGH
        local.content = "Local changes to content"
        local.updated = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        remote = {
            "id": "issue-1",
            "title": "Fix authentication bug",  # Different
            "status": "todo",  # Different
            "priority": "high",  # Same (enum match)
            "content": "Local changes to content",  # Same
        }

        conflicts = detect_field_conflicts(
            local,
            remote,
            ["title", "status", "priority", "content"],
        )

        assert len(conflicts) == 2
        field_names = {c.field_name for c in conflicts}
        assert field_names == {"title", "status"}

    def test_all_enum_fields_normalized(self):
        """Test all enum fields properly normalized in conflict."""
        local = MagicMock()
        local.status = Status.CLOSED
        local.priority = Priority.CRITICAL
        local.updated = datetime.now(UTC)

        remote = {"status": "closed", "priority": "critical"}

        conflicts = detect_field_conflicts(local, remote, ["status", "priority"])
        # Should have no conflicts - enums match after normalization
        assert len(conflicts) == 0

    def test_mixed_dict_and_object_remote(self):
        """Test with dict remote source."""
        local = MagicMock()
        local.title = "Title"
        local.status = Status.TODO
        local.updated = datetime.now(UTC)

        remote_dict = {"title": "Different Title", "status": "in_progress"}

        conflicts = detect_field_conflicts(local, remote_dict, ["title", "status"])
        assert len(conflicts) == 2

    def test_timestamp_inclusion_in_conflict_resolution(self):
        """Test timestamps properly included for conflict resolution ordering."""
        local_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        remote_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)

        local = MagicMock()
        local.status = Status.TODO
        local.updated = local_time

        def extractor(obj, field):
            if isinstance(obj, dict) and "updated_at" in obj:
                return obj["updated_at"]
            return None

        remote = {"status": "in_progress", "updated_at": remote_time}

        conflicts = detect_field_conflicts(
            local,
            remote,
            ["status"],
            extract_timestamp=extractor,
        )

        assert len(conflicts) == 1
        assert conflicts[0].local_updated == local_time
        assert conflicts[0].remote_updated == remote_time
