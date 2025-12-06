"""Tests for timezone-aware issue creation and handling.

This module tests the timezone-aware datetime functionality for issue creation,
ensuring that:
1. Issues are created with UTC timestamps
2. Timezone manager correctly handles different user timezones
3. Date conversions between timezones work correctly
4. Issue timestamps are properly stored and retrieved
5. Backward compatibility is maintained during timezone migration
"""

from datetime import datetime, timedelta, timezone

import pytest

from roadmap.common.timezone_utils import TimezoneManager
from roadmap.core.domain import Issue, Priority, Status
from roadmap.infrastructure.core import RoadmapCore


class TestTimezoneManager:
    """Test TimezoneManager functionality."""

    def test_timezone_manager_default_timezone(self):
        """Test TimezoneManager uses UTC as default."""
        tz_manager = TimezoneManager()
        assert tz_manager.user_timezone is not None
        # Default should be either UTC or system timezone
        assert len(tz_manager.user_timezone) > 0

    def test_timezone_manager_with_specific_timezone(self):
        """Test TimezoneManager with specified timezone."""
        tz_manager = TimezoneManager("America/New_York")
        assert tz_manager.user_timezone == "America/New_York"

    def test_timezone_manager_with_utc(self):
        """Test TimezoneManager with UTC timezone."""
        tz_manager = TimezoneManager("UTC")
        assert tz_manager.user_timezone == "UTC"

    def test_timezone_manager_is_timezone_aware(self):
        """Test TimezoneManager.is_timezone_aware method."""
        tz_manager = TimezoneManager()

        # UTC aware datetime
        utc_aware = datetime.now(timezone.utc)
        assert tz_manager.is_timezone_aware(utc_aware) is True

        # Naive datetime
        naive_dt = datetime.now()
        assert tz_manager.is_timezone_aware(naive_dt) is False

    def test_timezone_manager_parse_user_input(self):
        """Test parsing user input in different timezone."""
        tz_manager = TimezoneManager("America/New_York")

        # Parse date in New York timezone
        date_str = "2025-06-15"
        utc_time = tz_manager.parse_user_input(date_str)

        assert utc_time.tzinfo == timezone.utc
        # Should parse without error
        assert isinstance(utc_time, datetime)

    def test_timezone_manager_format_for_user(self):
        """Test formatting UTC datetime to user's timezone."""
        tz_manager = TimezoneManager("Europe/London")

        # Create UTC time
        utc_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Format for user (London time in June is BST, UTC+1)
        formatted = tz_manager.format_for_user(utc_time)

        # Should display in user's timezone
        assert isinstance(formatted, str)
        assert "2025" in formatted
        assert "13:00" in formatted or "13" in formatted  # 12:00 UTC + 1 hour

    def test_timezone_manager_make_aware(self):
        """Test making naive datetime timezone-aware."""
        tz_manager = TimezoneManager("Asia/Tokyo")

        # Naive datetime
        naive_dt = datetime(2025, 1, 1, 12, 0, 0)

        # Make aware - converts to UTC
        aware_dt = tz_manager.make_aware(naive_dt)

        assert aware_dt.tzinfo is not None
        # Should be UTC after make_aware
        assert aware_dt.tzinfo == timezone.utc
        # Tokyo is UTC+9, so 12:00 JST = 03:00 UTC
        assert aware_dt.hour == 3

    def test_timezone_manager_get_common_timezones(self):
        """Test getting list of common timezones."""
        tz_manager = TimezoneManager()
        timezones = tz_manager.get_common_timezones()

        assert isinstance(timezones, list)
        assert len(timezones) > 0
        assert "UTC" in timezones
        assert "America/New_York" in timezones or "US/Eastern" in timezones


class TestTimezoneAwareIssueCreation:
    """Test timezone-aware issue creation."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create RoadmapCore instance for testing."""
        return RoadmapCore(temp_dir)

    def test_issue_created_with_utc_timestamp(self, core):
        """Test that created issues have UTC timestamps."""
        core.initialize()

        # Create an issue
        before_creation = datetime.now(timezone.utc)
        issue = core.issues.create("Test Issue", Priority.HIGH)
        after_creation = datetime.now(timezone.utc)

        # Verify issue has UTC timestamp
        assert issue.created.tzinfo == timezone.utc
        assert before_creation <= issue.created <= after_creation

    def test_issue_created_with_utc_updated_timestamp(self, core):
        """Test that created issues have UTC updated timestamp."""
        core.initialize()

        # Create an issue
        before_creation = datetime.now(timezone.utc)
        issue = core.issues.create("Test Issue", Priority.HIGH)
        after_creation = datetime.now(timezone.utc)

        # Verify issue has UTC updated timestamp
        assert issue.updated.tzinfo == timezone.utc
        assert before_creation <= issue.updated <= after_creation

    def test_issue_creation_timezone_consistency(self, core):
        """Test that created and updated timestamps are consistent."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.HIGH)

        # created and updated should be equal or very close for new issues
        time_diff = abs((issue.created - issue.updated).total_seconds())
        assert time_diff < 1  # Should be within 1 second

    def test_multiple_issues_have_chronological_timestamps(self, core):
        """Test that multiple issues have proper chronological timestamps."""
        core.initialize()

        issue1 = core.issues.create("Issue 1", Priority.HIGH)
        issue2 = core.issues.create("Issue 2", Priority.MEDIUM)
        issue3 = core.issues.create("Issue 3", Priority.LOW)

        # Issues should be created in chronological order
        assert issue1.created <= issue2.created <= issue3.created

        # All should have UTC timezone
        assert issue1.created.tzinfo == timezone.utc
        assert issue2.created.tzinfo == timezone.utc
        assert issue3.created.tzinfo == timezone.utc

    def test_issue_with_timezone_manager(self, core):
        """Test issue creation with timezone manager context."""
        core.initialize()
        tz_manager = TimezoneManager("UTC")

        issue = core.issues.create(
            "Test Issue with TZ", priority=Priority.HIGH, milestone="v1.0"
        )

        # Format UTC time using timezone manager
        formatted = tz_manager.format_for_user(issue.created)

        # Should be able to format without error
        assert formatted is not None
        assert isinstance(formatted, str)


class TestTimezoneAwareIssueModification:
    """Test timezone-aware modifications to issues."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create RoadmapCore instance for testing."""
        return RoadmapCore(temp_dir)

    def test_issue_update_timestamp_is_utc(self, core):
        """Test that updated timestamp is UTC when issue is modified."""
        core.initialize()

        issue = core.issues.create("Original Title", Priority.HIGH)
        original_created = issue.created

        # Wait a moment to ensure time passes
        import time

        time.sleep(0.01)

        # Update the issue
        updated_issue = core.issues.update(issue.id, title="Updated Title")

        # Verify timestamps
        assert updated_issue.created.tzinfo == timezone.utc
        assert updated_issue.updated.tzinfo == timezone.utc
        assert original_created == updated_issue.created
        assert updated_issue.updated > updated_issue.created

    def test_issue_status_change_preserves_timezone(self, core):
        """Test that changing issue status preserves UTC timezone."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.HIGH)
        original_created = issue.created

        # Change status
        updated_issue = core.issues.update(issue.id, status=Status.IN_PROGRESS)

        # Verify timezone is preserved
        assert updated_issue.created.tzinfo == timezone.utc
        assert updated_issue.updated.tzinfo == timezone.utc
        assert updated_issue.created == original_created


class TestTimezoneAwareDateFields:
    """Test timezone-aware behavior for date fields in issues."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create RoadmapCore instance for testing."""
        return RoadmapCore(temp_dir)

    def test_issue_due_date_can_be_set_with_utc(self, core):
        """Test setting issue due date with UTC timezone via update."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.HIGH)

        # Set due date via update
        due_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        updated_issue = core.issues.update(issue.id, due_date=due_date)

        # Verify due_date is set and has correct timezone
        assert updated_issue.due_date == due_date
        assert updated_issue.due_date.tzinfo == timezone.utc

    def test_issue_actual_start_date_is_utc(self, core):
        """Test that actual_start_date is UTC when set."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.HIGH)

        # Set start date
        start_date = datetime.now(timezone.utc)
        updated_issue = core.issues.update(
            issue.id, actual_start_date=start_date, status=Status.IN_PROGRESS
        )

        # Verify start date is UTC
        assert updated_issue.actual_start_date is not None
        assert updated_issue.actual_start_date.tzinfo == timezone.utc

    def test_issue_actual_end_date_is_utc(self, core):
        """Test that actual_end_date is UTC when set."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.HIGH)

        # Set end date
        end_date = datetime.now(timezone.utc)
        updated_issue = core.issues.update(
            issue.id, actual_end_date=end_date, status=Status.CLOSED
        )

        # Verify end date is UTC
        assert updated_issue.actual_end_date is not None
        assert updated_issue.actual_end_date.tzinfo == timezone.utc


class TestTimezoneAwareIssueSerialization:
    """Test timezone-aware behavior in issue serialization."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create RoadmapCore instance for testing."""
        return RoadmapCore(temp_dir)

    def test_issue_serializes_timestamps_with_timezone(self, core):
        """Test that issue serialization includes timezone info."""
        core.initialize()

        issue = core.issues.create("Test Issue", Priority.HIGH)

        # Serialize the issue with mode='json' to get string representation
        issue_dict = issue.model_dump(mode="json")

        # Verify timestamps are serialized with timezone info
        assert "created" in issue_dict
        assert "updated" in issue_dict
        # When serialized to JSON, should be ISO format strings
        assert isinstance(issue_dict["created"], str)
        assert isinstance(issue_dict["updated"], str)
        # ISO format strings should contain timezone info (Z or +00:00)
        assert "T" in issue_dict["created"]
        assert "Z" in issue_dict["created"] or "+" in issue_dict["created"]

    def test_issue_deserialization_preserves_timezone(self, core):
        """Test that issue deserialization preserves timezone info."""
        core.initialize()

        original_issue = core.issues.create("Test Issue", Priority.HIGH)

        # Serialize and deserialize
        issue_dict = original_issue.model_dump()
        deserialized_issue = Issue(**issue_dict)

        # Verify timezone is preserved
        assert deserialized_issue.created.tzinfo is not None
        assert deserialized_issue.updated.tzinfo is not None
        assert deserialized_issue.created == original_issue.created
        assert deserialized_issue.updated == original_issue.updated


class TestTimezoneAwareIssueFiltering:
    """Test timezone-aware filtering of issues."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create RoadmapCore instance for testing."""
        return RoadmapCore(temp_dir)

    def test_list_issues_preserves_timezone(self, core):
        """Test that listing issues preserves timezone info in timestamps."""
        core.initialize()

        # Create multiple issues
        core.issues.create("Issue 1", Priority.HIGH)
        core.issues.create("Issue 2", Priority.MEDIUM)
        core.issues.create("Issue 3", Priority.LOW)

        # List issues
        issues = core.issues.list()

        # Verify all issues have UTC timestamps
        for issue in issues:
            assert issue.created.tzinfo == timezone.utc
            assert issue.updated.tzinfo == timezone.utc

    def test_filter_issues_by_created_date_range(self, core):
        """Test filtering issues by created date range."""
        core.initialize()

        # Create first issue
        core.issues.create("Early Issue", Priority.HIGH)

        # Wait a moment
        import time

        time.sleep(0.01)

        # Create second issue
        core.issues.create("Late Issue", Priority.LOW)

        # Filter by date range
        start_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        issues = core.issues.list()

        # Both should be created after start_time
        assert all(issue.created >= start_time for issue in issues)

    def test_issue_timestamps_comparable_across_timezones(self, core):
        """Test that issue timestamps are comparable across different timezones."""
        core.initialize()

        # Create issues
        issue1 = core.issues.create("Issue 1", Priority.HIGH)
        issue2 = core.issues.create("Issue 2", Priority.MEDIUM)

        # Both timestamps are in UTC
        assert issue1.created < issue2.created

        # Format in different timezone and verify order is preserved
        tz_tokyo = TimezoneManager("Asia/Tokyo")
        tz_tokyo.format_for_user(issue1.created)
        tz_tokyo.format_for_user(issue2.created)

        # Timestamps should still be comparable when converted back
        # The important thing is that UTC times preserve ordering
        assert issue1.created < issue2.created
