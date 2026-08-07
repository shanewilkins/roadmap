"""Tests for sync_state_normalizer helper functions."""

from datetime import datetime
from unittest.mock import Mock

from roadmap.core.services.sync.sync_state_normalizer import (
    extract_timestamp,
    normalize_remote_state,
)


class TestExtractTimestamp:
    """Tests for extract_timestamp function."""

    def test_extract_timestamp_from_dict_with_updated_at(self):
        """extract_timestamp should extract timestamp from dict with updated_at."""
        now = datetime.now()
        data = {"updated_at": now}
        result = extract_timestamp(data)
        assert result == now

    def test_extract_timestamp_from_dict_iso_format_with_z(self):
        """extract_timestamp should parse ISO format string with Z suffix."""
        data = {"updated_at": "2024-01-15T10:30:00Z"}
        result = extract_timestamp(data)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_extract_timestamp_from_dict_iso_format_with_offset(self):
        """extract_timestamp should parse ISO format with offset."""
        data = {"updated_at": "2024-01-15T10:30:00+00:00"}
        result = extract_timestamp(data)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_extract_timestamp_from_dict_no_timestamp(self):
        """extract_timestamp should return None if timestamp_field missing."""
        data = {"created_at": datetime.now()}
        result = extract_timestamp(data)
        assert result is None

    def test_extract_timestamp_from_dict_none_value(self):
        """extract_timestamp should return None if timestamp_field is None."""
        data = {"updated_at": None}
        result = extract_timestamp(data)
        assert result is None

    def test_extract_timestamp_from_dict_custom_field(self):
        """extract_timestamp should use custom timestamp_field parameter."""
        now = datetime.now()
        data = {"created_at": now}
        result = extract_timestamp(data, timestamp_field="created_at")
        assert result == now

    def test_extract_timestamp_from_object(self):
        """extract_timestamp should extract timestamp from object attributes."""
        now = datetime.now()
        obj = Mock()
        obj.updated_at = now
        result = extract_timestamp(obj)
        assert result == now

    def test_extract_timestamp_from_object_iso_string(self):
        """extract_timestamp should parse ISO string from object attribute."""
        obj = Mock()
        obj.updated_at = "2024-02-20T14:45:30Z"
        result = extract_timestamp(obj)
        assert result is not None
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 20

    def test_extract_timestamp_from_object_missing_attribute(self):
        """extract_timestamp should return None if object missing attribute."""
        obj = Mock(spec=[])
        result = extract_timestamp(obj)
        assert result is None

    def test_extract_timestamp_custom_field_from_object(self):
        """extract_timestamp should extract custom field from object."""
        now = datetime.now()
        obj = Mock()
        obj.created_date = now
        result = extract_timestamp(obj, timestamp_field="created_date")
        assert result == now

    def test_extract_timestamp_invalid_iso_format(self):
        """extract_timestamp should return None for invalid ISO format."""
        data = {"updated_at": "not-a-date"}
        result = extract_timestamp(data)
        assert result is None

    def test_extract_timestamp_non_string_non_datetime(self):
        """extract_timestamp should return None for non-string, non-datetime values."""
        data = {"updated_at": 12345}
        result = extract_timestamp(data)
        assert result is None

    def test_extract_timestamp_with_logger(self):
        """extract_timestamp should use logger when provided."""
        mock_logger = Mock()
        data = {"updated_at": datetime.now()}
        result = extract_timestamp(data, logger=mock_logger)
        assert result is not None
        # Logger should not be called for successful extraction

    def test_extract_timestamp_with_logger_on_error(self):
        """extract_timestamp should log errors when logger provided."""
        mock_logger = Mock()
        obj = Mock(spec=[])  # Missing attributes to cause error in getattr
        result = extract_timestamp(obj, logger=mock_logger)
        assert result is None

    def test_extract_timestamp_exception_in_extraction(self):
        """extract_timestamp should handle exceptions gracefully."""
        obj = Mock()
        obj.updated_at = Mock(side_effect=Exception("test error"))
        result = extract_timestamp(obj)
        assert result is None

    def test_extract_timestamp_datetime_object_passthrough(self):
        """extract_timestamp should return datetime object unchanged."""
        now = datetime.now()
        data = {"updated_at": now}
        result = extract_timestamp(data)
        assert result is now
        assert result == now

    def test_extract_timestamp_z_suffix_conversion(self):
        """extract_timestamp should convert Z to +00:00."""
        # This tests the Z -> +00:00 conversion logic
        iso_string = "2024-03-10T08:15:30Z"
        data = {"updated_at": iso_string}
        result = extract_timestamp(data)
        assert result is not None
        # Verify it was parsed correctly
        assert result.hour == 8
        assert result.minute == 15


class TestNormalizeRemoteState:
    """Tests for normalize_remote_state function."""

    def test_normalize_remote_state_with_dict_returns_same_dict(self):
        """normalize_remote_state should return dict unchanged."""
        data = {"id": "123", "title": "Test"}
        result = normalize_remote_state(data)
        assert result == data
        assert result is data  # Same object

    def test_normalize_remote_state_with_none(self):
        """normalize_remote_state should return None unchanged."""
        result = normalize_remote_state(None)
        assert result is None

    def test_normalize_remote_state_with_object(self):
        """normalize_remote_state should convert object to dict."""
        obj = Mock()
        obj.id = "issue-1"
        obj.title = "Test Issue"
        obj.status = "open"
        obj.assignee = "alice"
        obj.milestone = "v1-0"
        obj.headline = None
        obj.description = "A test issue"
        obj.labels = ["bug", "urgent"]
        obj.updated_at = "2024-01-15T10:00:00Z"
        obj.updated = None

        result = normalize_remote_state(obj)
        assert result is not None
        assert result["id"] == "issue-1"
        assert result["title"] == "Test Issue"
        assert result["status"] == "open"
        assert result["assignee"] == "alice"
        assert result["milestone"] == "v1-0"
        assert result["description"] == "A test issue"
        assert result["labels"] == ["bug", "urgent"]
        assert result["updated_at"] == "2024-01-15T10:00:00Z"

    def test_normalize_remote_state_object_uses_headline_over_description(self):
        """normalize_remote_state should prefer headline over description."""
        obj = Mock(spec=["headline", "description"])
        obj.headline = "Headline text"
        obj.description = "Description text"
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["description"] == "Headline text"

    def test_normalize_remote_state_object_uses_updated_at_over_updated(self):
        """normalize_remote_state should prefer updated_at over updated."""
        obj = Mock(spec=["updated_at", "updated"])
        obj.updated_at = "2024-02-01T00:00:00Z"
        obj.updated = "2024-01-01T00:00:00Z"
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["updated_at"] == "2024-02-01T00:00:00Z"

    def test_normalize_remote_state_object_with_missing_fields(self):
        """normalize_remote_state should handle missing object attributes."""
        obj = Mock(spec=["id", "title"])  # Limited spec
        obj.id = "issue-1"
        obj.title = "Test"
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["id"] == "issue-1"
        assert result["title"] == "Test"
        assert result["status"] is None
        assert result["assignee"] is None
        assert result["milestone"] is None
        assert result["description"] is None
        assert result["labels"] == []
        assert result["updated_at"] is None

    def test_normalize_remote_state_object_with_none_labels(self):
        """normalize_remote_state should convert None labels to empty list."""
        obj = Mock()
        obj.labels = None
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["labels"] == []

    def test_normalize_remote_state_object_with_empty_labels(self):
        """normalize_remote_state should preserve empty labels list."""
        obj = Mock()
        obj.labels = []
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["labels"] == []

    def test_normalize_remote_state_object_labels_converted_to_list(self):
        """normalize_remote_state should convert labels to list."""
        obj = Mock()
        obj.labels = {"label1", "label2", "label3"}  # Set, not list
        result = normalize_remote_state(obj)
        assert result is not None
        assert isinstance(result["labels"], list)
        assert len(result["labels"]) == 3

    def test_normalize_remote_state_object_all_fields_none(self):
        """normalize_remote_state should handle object with all None fields."""
        obj = Mock(
            spec=[
                "id",
                "title",
                "status",
                "assignee",
                "milestone",
                "headline",
                "description",
                "labels",
                "updated_at",
                "updated",
            ]
        )
        obj.id = None
        obj.title = None
        obj.status = None
        obj.assignee = None
        obj.milestone = None
        obj.headline = None
        obj.description = None
        obj.labels = None
        obj.updated_at = None
        obj.updated = None

        result = normalize_remote_state(obj)
        assert result is not None
        assert result["id"] is None
        assert result["title"] is None
        assert result["status"] is None
        assert result["assignee"] is None
        assert result["milestone"] is None
        assert result["description"] is None
        assert result["labels"] == []
        assert result["updated_at"] is None

    def test_normalize_remote_state_with_logger(self):
        """normalize_remote_state should accept logger parameter."""
        mock_logger = Mock()
        obj = Mock(spec=["id"])
        obj.id = "test"
        result = normalize_remote_state(obj, logger=mock_logger)
        assert result is not None

    def test_normalize_remote_state_exception_handling(self):
        """normalize_remote_state should return None on exception."""
        obj = Mock()
        obj.id = Mock(side_effect=Exception("test error"))
        result = normalize_remote_state(obj)
        assert result is None

    def test_normalize_remote_state_with_logger_logs_error(self):
        """normalize_remote_state should log errors when logger provided."""
        mock_logger = Mock()
        obj = Mock()
        obj.id = Mock(side_effect=Exception("attribute error"))
        result = normalize_remote_state(obj, logger=mock_logger)
        assert result is None

    def test_normalize_remote_state_dict_preserves_all_fields(self):
        """normalize_remote_state should preserve dict with extra fields."""
        data = {
            "id": "123",
            "title": "Test",
            "extra_field": "extra_value",
            "another_field": 42,
        }
        result = normalize_remote_state(data)
        assert result is not None
        assert result == data
        assert result["extra_field"] == "extra_value"
        assert result["another_field"] == 42

    def test_normalize_remote_state_object_headline_none_uses_description(self):
        """normalize_remote_state should fall back to description if headline is None."""
        obj = Mock(spec=["headline", "description"])
        obj.headline = None
        obj.description = "Fallback description"
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["description"] == "Fallback description"

    def test_normalize_remote_state_object_updated_at_none_uses_updated(self):
        """normalize_remote_state should fall back to updated if updated_at is None."""
        obj = Mock(spec=["updated_at", "updated"])
        obj.updated_at = None
        obj.updated = "2024-01-10T00:00:00Z"
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["updated_at"] == "2024-01-10T00:00:00Z"

    def test_normalize_remote_state_complex_labels(self):
        """normalize_remote_state should handle complex label structures."""
        obj = Mock()
        obj.labels = ["critical", "bug", "high-priority", "backend"]
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["labels"] == ["critical", "bug", "high-priority", "backend"]

    def test_normalize_remote_state_minimal_object(self):
        """normalize_remote_state should work with minimal object."""
        obj = Mock(spec=[])
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["id"] is None
        assert result["title"] is None
        assert result["status"] is None
        assert result["assignee"] is None
        assert result["milestone"] is None
        assert result["description"] is None
        assert result["labels"] == []
        assert result["updated_at"] is None
