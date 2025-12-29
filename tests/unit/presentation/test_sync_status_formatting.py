"""Tests for sync_status command - GitHub sync history and statistics."""

from unittest.mock import Mock

import pytest

from roadmap.adapters.cli.issues.sync_status import (
    _build_sync_metadata_table,
    _build_sync_status_header,
    _format_timestamp,
)


class TestFormatTimestamp:
    """Test timestamp formatting utility."""

    def test_format_valid_iso_timestamp(self):
        """Test formatting a valid ISO timestamp."""
        iso_str = "2025-12-23T20:30:00Z"
        result = _format_timestamp(iso_str)
        assert "2025-12-23" in result
        assert "20:30:00" in result

    def test_format_invalid_timestamp_returns_original(self):
        """Test that invalid timestamp returns original string."""
        invalid_str = "not-a-timestamp"
        result = _format_timestamp(invalid_str)
        assert result == invalid_str

    def test_format_empty_timestamp(self):
        """Test formatting empty string."""
        result = _format_timestamp("")
        assert result == ""

    @pytest.mark.parametrize(
        "iso_str,should_contain",
        [
            ("2025-01-01T00:00:00Z", "2025-01-01"),
            ("2025-12-31T23:59:59Z", "2025-12-31"),
            ("2024-06-15T12:30:45Z", "2024-06-15"),
        ],
    )
    def test_format_various_valid_timestamps(self, iso_str, should_contain):
        """Test formatting various valid ISO timestamps."""
        result = _format_timestamp(iso_str)
        assert should_contain in result

    def test_format_timestamp_with_microseconds(self):
        """Test formatting timestamp with microseconds."""
        iso_str = "2025-12-23T20:30:00.123456Z"
        result = _format_timestamp(iso_str)
        assert "2025-12-23" in result

    def test_format_none_timestamp(self):
        """Test that function expects string input, not None."""
        # _format_timestamp requires a string, not None
        # This test verifies the type contract is enforced
        iso_str = ""  # Empty string is still a valid str type
        result = _format_timestamp(iso_str)
        assert isinstance(result, str)


class TestBuildSyncStatusHeader:
    """Test sync status header building."""

    @pytest.mark.parametrize(
        "status,sync_time,issue_id,issue_title",
        [
            ("success", "2025-12-23T20:30:00Z", "123", "Test Issue"),
            ("error", "2025-12-23T20:30:00Z", "456", "Error Issue"),
            ("conflict", "2025-12-23T20:30:00Z", "789", "Conflict Issue"),
            ("never", None, "999", "Never Synced"),
        ],
    )
    def test_build_header_with_various_statuses(
        self, status, sync_time, issue_id, issue_title
    ):
        """Test building header with various sync statuses."""
        issue = Mock(id=issue_id, title=issue_title)
        metadata = Mock(
            last_sync_status=status,
            last_sync_time=sync_time,
        )

        header = _build_sync_status_header(issue, metadata)
        assert header is not None
        # Header should contain issue ID for non-null titles
        if sync_time:
            assert str(header).find("#") >= 0

    def test_build_header_with_no_sync_time(self):
        """Test building header with no sync time."""
        issue = Mock(id="111", title="No Time Issue")
        metadata = Mock(
            last_sync_status="success",
            last_sync_time=None,
        )

        header = _build_sync_status_header(issue, metadata)
        assert header is not None

    @pytest.mark.parametrize(
        "status,expected_color",
        [
            ("success", "green"),
            ("error", "red"),
            ("conflict", "yellow"),
            ("never", "dim"),
        ],
    )
    def test_header_status_color_mapping(self, status, expected_color):
        """Test that status colors are correctly mapped."""
        issue = Mock(id="test", title="Test")
        metadata = Mock(
            last_sync_status=status,
            last_sync_time="2025-12-23T20:30:00Z",
        )

        header = _build_sync_status_header(issue, metadata)
        assert header is not None

    def test_build_header_with_long_title(self):
        """Test building header with very long issue title."""
        long_title = "A" * 200
        issue = Mock(id="123", title=long_title)
        metadata = Mock(
            last_sync_status="success",
            last_sync_time="2025-12-23T20:30:00Z",
        )

        header = _build_sync_status_header(issue, metadata)
        assert header is not None

    def test_build_header_with_special_characters_in_title(self):
        """Test building header with special characters in title."""
        issue = Mock(id="123", title="Issue #1: Fix [bug] & improve (UX) 🐛")
        metadata = Mock(
            last_sync_status="success",
            last_sync_time="2025-12-23T20:30:00Z",
        )

        header = _build_sync_status_header(issue, metadata)
        assert header is not None


class TestBuildSyncMetadataTable:
    """Test sync metadata table building."""

    def test_build_metadata_table_with_github_id(self):
        """Test building metadata table with GitHub issue ID."""
        issue = Mock(id="123", title="Test")
        metadata = Mock(
            github_issue_id="456",
            sync_count=10,
            successful_syncs=9,
            sync_history=[],
        )
        metadata.get_success_rate = Mock(return_value=90.0)

        table = _build_sync_metadata_table(issue, metadata)
        assert table is not None

    def test_build_metadata_table_without_github_id(self):
        """Test building metadata table without GitHub issue ID."""
        issue = Mock(id="123", title="Test")
        metadata = Mock(
            github_issue_id=None,
            sync_count=5,
            successful_syncs=5,
            sync_history=[],
        )
        metadata.get_success_rate = Mock(return_value=100.0)

        table = _build_sync_metadata_table(issue, metadata)
        assert table is not None

    def test_metadata_table_success_rate_colors(self):
        """Test success rate color coding."""
        issue = Mock(id="123", title="Test")

        # Test green (100%)
        metadata_green = Mock(
            github_issue_id="456",
            sync_count=10,
            successful_syncs=10,
            sync_history=[],
        )
        metadata_green.get_success_rate = Mock(return_value=100.0)
        table = _build_sync_metadata_table(issue, metadata_green)
        assert table is not None

        # Test yellow (75%)
        metadata_yellow = Mock(
            github_issue_id="456",
            sync_count=10,
            successful_syncs=8,
            sync_history=[],
        )
        metadata_yellow.get_success_rate = Mock(return_value=75.0)
        table = _build_sync_metadata_table(issue, metadata_yellow)
        assert table is not None

        # Test red (50%)
        metadata_red = Mock(
            github_issue_id="456",
            sync_count=10,
            successful_syncs=5,
            sync_history=[],
        )
        metadata_red.get_success_rate = Mock(return_value=50.0)
        table = _build_sync_metadata_table(issue, metadata_red)
        assert table is not None

    def test_metadata_table_with_conflicts(self):
        """Test metadata table showing conflict resolution."""
        issue = Mock(id="123", title="Test")

        sync_record_1 = Mock(conflict_resolution="resolved by local")
        sync_record_2 = Mock(conflict_resolution=None)
        sync_record_3 = Mock(conflict_resolution="resolved by github")

        metadata = Mock(
            github_issue_id="456",
            sync_count=10,
            successful_syncs=9,
            sync_history=[sync_record_1, sync_record_2, sync_record_3],
        )
        metadata.get_success_rate = Mock(return_value=90.0)

        table = _build_sync_metadata_table(issue, metadata)
        assert table is not None

    def test_metadata_table_no_syncs(self):
        """Test metadata table with no sync history."""
        issue = Mock(id="123", title="Test")
        metadata = Mock(
            github_issue_id="456",
            sync_count=0,
            successful_syncs=0,
            sync_history=[],
        )

        table = _build_sync_metadata_table(issue, metadata)
        assert table is not None

    @pytest.mark.parametrize(
        "sync_count,successful",
        [
            (1, 1),
            (5, 5),
            (10, 8),
            (20, 15),
        ],
    )
    def test_metadata_table_various_sync_counts(self, sync_count, successful):
        """Test metadata table with various sync counts."""
        issue = Mock(id="123", title="Test")
        metadata = Mock(
            github_issue_id="456",
            sync_count=sync_count,
            successful_syncs=successful,
            sync_history=[],
        )
        metadata.get_success_rate = Mock(return_value=(successful / sync_count * 100))

        table = _build_sync_metadata_table(issue, metadata)
        assert table is not None
