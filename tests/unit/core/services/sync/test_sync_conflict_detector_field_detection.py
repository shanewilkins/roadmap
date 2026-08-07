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
