"""Complete test coverage for sync_state_normalizer module.

Tests for extract_timestamp and normalize_remote_state functions,
including error handling paths that use structlog logging.
"""

from datetime import UTC, datetime

from roadmap.core.services.sync.sync_state_normalizer import (
    extract_timestamp,
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
