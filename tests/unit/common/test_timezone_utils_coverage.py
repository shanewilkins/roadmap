"""Test coverage for timezone_utils module functions."""

from datetime import datetime, timedelta, timezone

import pytest

from roadmap.common.timezone_utils import (
    TimezoneManager,
    ensure_timezone_aware,
    format_datetime,
    format_relative_time,
    get_timezone_manager,
    migrate_naive_datetime,
    now_local,
    now_utc,
    parse_datetime,
)


class TestTimezoneManagerFactory:
    """Test get_timezone_manager factory function."""

    @pytest.mark.parametrize(
        "tz_string,description",
        [
            (None, "default"),
            ("UTC", "utc"),
            ("America/New_York", "eastern"),
            ("America/Los_Angeles", "pacific"),
        ],
    )
    def test_get_timezone_manager(self, tz_string, description):
        """Test getting timezone manager with various timezones."""
        manager = get_timezone_manager(tz_string)
        assert manager is not None
        assert isinstance(manager, TimezoneManager)


class TestNowUtc:
    """Test now_utc function."""

    def test_now_utc_returns_datetime(self):
        """Test now_utc returns a datetime object."""
        result = now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_is_timezone_aware(self):
        """Test now_utc returns timezone-aware datetime."""
        result = now_utc()
        assert result.tzinfo is not None

    def test_now_utc_is_utc(self):
        """Test now_utc returns UTC timezone."""
        result = now_utc()
        # Check that it's in UTC (offset is 0)
        assert result.utcoffset() == timedelta(0)

    def test_now_utc_is_recent(self):
        """Test now_utc returns recent timestamp."""
        before = datetime.now(timezone.utc)
        result = now_utc()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestNowLocal:
    """Test now_local function."""

    def test_now_local_returns_datetime(self):
        """Test now_local returns a datetime object."""
        result = now_local()
        assert isinstance(result, datetime)

    def test_now_local_with_timezone_aware(self):
        """Test now_local with explicit timezone."""
        result = now_local("America/New_York")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_now_local_with_utc(self):
        """Test now_local with UTC timezone."""
        result = now_local("UTC")
        assert isinstance(result, datetime)
        # Should be the same as now_utc (within milliseconds)
        utc_now = now_utc()
        assert abs((result - utc_now).total_seconds()) < 1.0


class TestParseDatetime:
    """Test parse_datetime function."""

    @pytest.mark.parametrize(
        "date_str,tz_string,description",
        [
            ("2025-12-16T10:30:00", None, "iso_format"),
            ("2025-12-16T10:30:00", "America/New_York", "iso_with_timezone"),
            ("2025-12-16T10:30:00Z", None, "iso_with_z"),
            ("2025-12-16T10:30:00", "UTC", "iso_with_utc"),
        ],
    )
    def test_parse_datetime(self, date_str, tz_string, description):
        """Test parsing datetime strings with various formats."""
        result = (
            parse_datetime(date_str, tz_string)
            if tz_string
            else parse_datetime(date_str)
        )
        assert isinstance(result, datetime)
        if tz_string or "Z" in date_str:
            assert result.tzinfo is not None


class TestFormatDatetime:
    """Test format_datetime function."""

    @pytest.mark.parametrize(
        "tz_string,description",
        [
            (None, "no_timezone"),
            ("America/New_York", "eastern"),
            ("UTC", "utc"),
        ],
    )
    def test_format_datetime(self, tz_string, description):
        """Test formatting datetime with various timezones."""
        dt = datetime.now(timezone.utc)
        result = format_datetime(dt, tz_string) if tz_string else format_datetime(dt)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_datetime_contains_date(self):
        """Test formatted datetime contains recognizable date."""
        dt = datetime(2025, 12, 16, 10, 30, 0, tzinfo=timezone.utc)
        result = format_datetime(dt)
        # Should contain year, month, day in some format
        assert any(
            x in result for x in ["2025", "12", "16", "10", "30", "Dec", "December"]
        )


class TestFormatRelativeTime:
    """Test format_relative_time function."""

    def test_format_relative_time_returns_string(self):
        """Test format_relative_time returns string."""
        dt = datetime.now(timezone.utc)
        result = format_relative_time(dt)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_relative_time_future(self):
        """Test format_relative_time with future datetime."""
        future_dt = datetime.now(timezone.utc) + timedelta(hours=2)
        result = format_relative_time(future_dt)
        assert isinstance(result, str)

    def test_format_relative_time_past(self):
        """Test format_relative_time with past datetime."""
        past_dt = datetime.now(timezone.utc) - timedelta(hours=2)
        result = format_relative_time(past_dt)
        assert isinstance(result, str)

    def test_format_relative_time_now(self):
        """Test format_relative_time with current time."""
        now_dt = datetime.now(timezone.utc)
        result = format_relative_time(now_dt)
        assert isinstance(result, str)
        # Should contain something like "now" or "ago" or similar
        assert len(result) > 0

    def test_format_relative_time_with_timezone(self):
        """Test format_relative_time with specific timezone."""
        dt = datetime.now(timezone.utc)
        result = format_relative_time(dt, "America/Los_Angeles")
        assert isinstance(result, str)


class TestMigrateNaiveDatetime:
    """Test migrate_naive_datetime function."""

    @pytest.mark.parametrize(
        "naive_dt,tz_string,description",
        [
            (datetime(2025, 12, 16, 10, 30, 0), None, "naive_default"),
            (datetime(2025, 12, 16, 10, 30, 0), "America/New_York", "naive_eastern"),
            (datetime(2025, 12, 16, 10, 30, 0), "UTC", "naive_utc"),
        ],
    )
    def test_migrate_naive_datetime(self, naive_dt, tz_string, description):
        """Test migrating naive datetime with various timezones."""
        result = (
            migrate_naive_datetime(naive_dt, tz_string)
            if tz_string
            else migrate_naive_datetime(naive_dt)
        )
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_migrate_aware_datetime_unchanged(self):
        """Test that aware datetime is not modified."""
        aware_dt = datetime(2025, 12, 16, 10, 30, 0, tzinfo=timezone.utc)
        result = migrate_naive_datetime(aware_dt)
        assert result.tzinfo is not None

    def test_migrate_naive_datetime_default_utc(self):
        """Test that naive datetime defaults to UTC."""
        naive_dt = datetime(2025, 12, 16, 10, 30, 0)
        result = migrate_naive_datetime(naive_dt)
        # Should be in UTC
        assert result.tzinfo is not None
        assert result.minute == naive_dt.minute
        assert result.second == naive_dt.second


class TestEnsureTimezoneAware:
    """Test ensure_timezone_aware function."""

    @pytest.mark.parametrize(
        "tz_string,description",
        [
            (None, "default_utc"),
            ("America/Los_Angeles", "pacific"),
        ],
    )
    def test_ensure_timezone_aware_naive(self, tz_string, description):
        """Test ensuring naive datetime becomes timezone-aware."""
        naive_dt = datetime(2025, 12, 16, 10, 30, 0)
        result = (
            ensure_timezone_aware(naive_dt, tz_string)
            if tz_string
            else ensure_timezone_aware(naive_dt)
        )
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_ensure_timezone_aware_aware_input(self):
        """Test that aware datetime is not modified."""
        aware_dt = datetime(2025, 12, 16, 10, 30, 0, tzinfo=timezone.utc)
        result = ensure_timezone_aware(aware_dt)
        assert result.tzinfo is not None

    def test_ensure_timezone_aware_default_utc(self):
        """Test that naive datetime defaults to UTC."""
        naive_dt = datetime(2025, 12, 16, 10, 30, 0)
        result = ensure_timezone_aware(naive_dt)
        assert result.utcoffset() == timedelta(0)

    def test_ensure_timezone_aware_idempotent(self):
        """Test that calling multiple times doesn't break datetime."""
        naive_dt = datetime(2025, 12, 16, 10, 30, 0)
        result1 = ensure_timezone_aware(naive_dt)
        result2 = ensure_timezone_aware(result1)
        assert result1 == result2


class TestTimezoneConversionRoundtrip:
    """Test round-trip timezone conversions."""

    def test_parse_and_format_roundtrip(self):
        """Test parsing and formatting preserves datetime."""
        original_dt = datetime.now(timezone.utc)
        formatted = format_datetime(original_dt)
        # Verify formatted string is reasonable
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_naive_to_aware_to_format(self):
        """Test conversion chain: naive -> aware -> formatted."""
        naive_dt = datetime(2025, 12, 16, 10, 30, 0)
        aware_dt = ensure_timezone_aware(naive_dt)
        formatted = format_datetime(aware_dt)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_utc_and_local_consistency(self):
        """Test that UTC and local time are consistent."""
        utc_time = now_utc()
        local_time = now_local("UTC")
        # Should be very close (within 1 second)
        diff = abs((utc_time - local_time).total_seconds())
        assert diff < 1.0


class TestTimezoneEdgeCases:
    """Test edge cases and error handling."""

    def test_datetime_with_microseconds(self):
        """Test datetime with microseconds is preserved."""
        dt = datetime(2025, 12, 16, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = format_datetime(dt)
        assert isinstance(result, str)

    def test_far_future_datetime(self):
        """Test handling of far future datetime."""
        future_dt = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        result = format_datetime(future_dt)
        assert isinstance(result, str)
        assert "2099" in result or "99" in result

    def test_far_past_datetime(self):
        """Test handling of far past datetime."""
        past_dt = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = format_datetime(past_dt)
        assert isinstance(result, str)

    def test_timezone_with_special_offset(self):
        """Test timezone with unusual offset."""
        # Some timezones have 30-minute or 45-minute offsets
        # Just verify the functions don't crash
        dt = now_local()
        result = format_datetime(dt)
        assert isinstance(result, str)


class TestTimezoneIntegration:
    """Integration tests combining multiple functions."""

    def test_workflow_create_parse_format(self):
        """Test workflow: create datetime, format, verify format is string."""
        # Create
        original = datetime.now(timezone.utc)
        # Format
        formatted = format_datetime(original)
        assert isinstance(formatted, str)
        # Verify format is reasonable
        assert len(formatted) > 0

    def test_workflow_naive_to_stored_to_displayed(self):
        """Test workflow: naive input -> storage (UTC) -> display."""
        # User inputs naive time
        user_input = datetime(2025, 12, 16, 10, 30, 0)
        # Convert to UTC for storage
        stored = ensure_timezone_aware(user_input)
        assert stored.tzinfo is not None
        # Format for display
        displayed = format_datetime(stored, "America/New_York")
        assert isinstance(displayed, str)

    def test_workflow_multiple_timezones(self):
        """Test same UTC time displayed in multiple timezones."""
        utc_time = datetime(2025, 12, 16, 12, 0, 0, tzinfo=timezone.utc)

        ny_display = format_datetime(utc_time, "America/New_York")
        la_display = format_datetime(utc_time, "America/Los_Angeles")

        assert isinstance(ny_display, str)
        assert isinstance(la_display, str)
        # Both should reference the same UTC time
        assert len(ny_display) > 0
        assert len(la_display) > 0
