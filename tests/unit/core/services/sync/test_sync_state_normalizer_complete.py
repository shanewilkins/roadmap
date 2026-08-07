"""Complete test coverage for sync_state_normalizer module.

Tests for extract_timestamp and normalize_remote_state functions,
including error handling paths that use structlog logging.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from roadmap.core.services.sync.sync_state_normalizer import (
    extract_timestamp,
    normalize_remote_state,
)


class TestExtractTimestampBasic:
    """Tests for basic extract_timestamp functionality."""

    def test_extract_timestamp_from_dict_with_datetime_object(self):
        """Extract a datetime object from dict."""
        now = datetime.now(UTC)
        data = {"updated_at": now}
        result = extract_timestamp(data, "updated_at")
        assert result == now

    def test_extract_timestamp_from_dict_with_iso_string(self):
        """Extract and parse ISO string from dict."""
        data = {"updated_at": "2024-01-15T10:30:45+00:00"}
        result = extract_timestamp(data, "updated_at")
        assert result == datetime.fromisoformat("2024-01-15T10:30:45+00:00")

    def test_extract_timestamp_from_dict_with_z_suffix(self):
        """Extract and parse ISO string with Z suffix."""
        data = {"updated_at": "2024-01-15T10:30:45Z"}
        result = extract_timestamp(data, "updated_at")
        # Z is converted to +00:00
        assert result is not None
        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_extract_timestamp_from_dict_missing_field(self):
        """Extract from dict with missing timestamp field."""
        data = {"title": "test"}
        result = extract_timestamp(data, "updated_at")
        assert result is None

    def test_extract_timestamp_from_dict_with_none_value(self):
        """Extract from dict where field is None."""
        data = {"updated_at": None}
        result = extract_timestamp(data, "updated_at")
        assert result is None

    def test_extract_timestamp_from_object_with_datetime(self):
        """Extract datetime from object attribute."""
        obj = MagicMock()
        now = datetime.now(UTC)
        obj.updated_at = now
        result = extract_timestamp(obj, "updated_at")
        assert result == now

    def test_extract_timestamp_from_object_with_iso_string(self):
        """Extract and parse ISO string from object attribute."""
        obj = MagicMock()
        obj.updated_at = "2024-01-15T10:30:45+00:00"
        result = extract_timestamp(obj, "updated_at")
        assert result == datetime.fromisoformat("2024-01-15T10:30:45+00:00")

    def test_extract_timestamp_from_object_missing_attribute(self):
        """Extract from object without timestamp attribute."""
        obj = MagicMock(spec=[])  # Empty spec, no attributes
        result = extract_timestamp(obj, "updated_at")
        assert result is None

    def test_extract_timestamp_with_custom_field_name(self):
        """Extract using custom field name."""
        data = {"updated": "2024-01-15T10:30:45+00:00"}
        result = extract_timestamp(data, "updated")
        assert result is not None
        assert result.year == 2024

    def test_extract_timestamp_with_invalid_string_format(self):
        """Extract with invalid timestamp string returns None."""
        data = {"updated_at": "not-a-timestamp"}
        result = extract_timestamp(data, "updated_at")
        assert result is None

    def test_extract_timestamp_with_non_datetime_non_string(self):
        """Extract with non-datetime, non-string value returns None."""
        data = {"updated_at": 12345}
        result = extract_timestamp(data, "updated_at")
        assert result is None


class TestExtractTimestampErrorHandling:
    """Tests for error handling paths in extract_timestamp."""

    def test_extract_timestamp_logs_error_when_logger_provided(self):
        """Logger error is logged when exception occurs during extraction."""
        mock_logger = MagicMock()
        data = {"updated_at": "invalid-date"}
        result = extract_timestamp(data, "updated_at", logger=mock_logger)
        assert result is None
        # Logger should be called with debug message
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "timestamp_extraction_error"
        assert "field" in call_args[1]
        assert "error" in call_args[1]

    def test_extract_timestamp_handles_logger_exception(self):
        """Logger exception is handled gracefully."""
        mock_logger = MagicMock()
        mock_logger.debug.side_effect = Exception("Logger failed")
        mock_logger.error = MagicMock()
        data = {"updated_at": "invalid-date"}
        result = extract_timestamp(data, "updated_at", logger=mock_logger)
        assert result is None
        # Error logger should be called when debug fails
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "logger_failed"


class TestNormalizeRemoteStateBasic:
    """Tests for basic normalize_remote_state functionality."""

    def test_normalize_remote_state_with_none(self):
        """Normalize None returns None."""
        result = normalize_remote_state(None)
        assert result is None

    def test_normalize_remote_state_with_dict(self):
        """Normalize dict returns same dict."""
        data = {
            "id": "123",
            "title": "Test",
            "status": "open",
        }
        result = normalize_remote_state(data)
        assert result == data

    def test_normalize_remote_state_with_object_all_fields(self):
        """Normalize object with all fields."""
        obj = MagicMock()
        obj.id = "123"
        obj.title = "Test Issue"
        obj.status = "open"
        obj.assignee = "alice"
        obj.milestone = "v1-0"
        obj.headline = "Headline text"
        obj.description = "Description text"
        obj.labels = ["bug", "urgent"]
        obj.updated_at = datetime.now(UTC)

        result = normalize_remote_state(obj)
        assert result is not None
        assert result["id"] == "123"
        assert result["title"] == "Test Issue"
        assert result["status"] == "open"
        assert result["assignee"] == "alice"
        assert result["milestone"] == "v1-0"
        assert result["description"] == "Headline text"  # headline takes precedence
        assert result["labels"] == ["bug", "urgent"]
        assert isinstance(result["updated_at"], datetime)

    def test_normalize_remote_state_object_missing_fields(self):
        """Normalize object with missing fields uses None."""
        obj = MagicMock(spec=[])  # Empty spec
        result = normalize_remote_state(obj)
        assert result is not None
        assert result["id"] is None
        assert result["title"] is None
        assert result["status"] is None

    def test_normalize_remote_state_uses_headline_over_description(self):
        """When both headline and description exist, headline is preferred."""
        obj = MagicMock()
        obj.id = "123"
        obj.title = "Test"
        obj.status = "open"
        obj.assignee = None
        obj.milestone = None
        obj.headline = "This is headline"
        obj.description = "This is description"
        obj.labels = []
        obj.updated_at = None
        obj.updated = None

        result = normalize_remote_state(obj)
        assert result is not None
        assert result["description"] == "This is headline"

    def test_normalize_remote_state_uses_updated_at_over_updated(self):
        """When both updated_at and updated exist, updated_at is preferred."""
        now = datetime.now(UTC)
        yesterday = datetime.now(UTC)
        obj = MagicMock()
        obj.id = "123"
        obj.title = "Test"
        obj.status = "open"
        obj.assignee = None
        obj.milestone = None
        obj.headline = None
        obj.description = None
        obj.labels = []
        obj.updated_at = now
        obj.updated = yesterday

        result = normalize_remote_state(obj)
        assert result is not None
        assert result["updated_at"] == now

    def test_normalize_remote_state_handles_none_labels(self):
        """Normalize object with None labels converts to empty list."""
        obj = MagicMock()
        obj.id = "123"
        obj.title = "Test"
        obj.status = "open"
        obj.assignee = None
        obj.milestone = None
        obj.headline = None
        obj.description = None
        obj.labels = None
        obj.updated_at = None
        obj.updated = None

        result = normalize_remote_state(obj)
        assert result is not None
        assert result["labels"] == []


class TestNormalizeRemoteStateErrorHandling:
    """Tests for error handling in normalize_remote_state."""

    def test_normalize_remote_state_error_returns_none(self):
        """Exception during normalization returns None."""
        obj = MagicMock()
        # Simulate getattr raising exception
        obj.id.__class__ = property  # Force getattr to raise

        # Actually, let's use a different approach - create an object that fails on getattr
        class FailingObject:
            def __getattr__(self, name):
                raise RuntimeError("Attribute access failed")

        result = normalize_remote_state(FailingObject())
        assert result is None

    def test_normalize_remote_state_logs_error_when_logger_provided(self):
        """Logger error is logged when exception occurs."""
        mock_logger = MagicMock()

        class FailingObject:
            def __getattr__(self, name):
                raise RuntimeError("Attribute access failed")

        result = normalize_remote_state(FailingObject(), logger=mock_logger)
        assert result is None
        # Logger should be called with debug message
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "normalize_remote_state_error"
        assert "error" in call_args[1]

    def test_normalize_remote_state_handles_logger_exception(self):
        """Logger exception during error logging is handled."""
        mock_logger = MagicMock()
        mock_logger.debug.side_effect = Exception("Logger failed")
        mock_logger.error = MagicMock()

        class FailingObject:
            def __getattr__(self, name):
                raise RuntimeError("Attribute access failed")

        result = normalize_remote_state(FailingObject(), logger=mock_logger)
        assert result is None
        # Error logger should be called when debug fails
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "logger_failed"
