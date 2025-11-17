"""Timezone utilities for the roadmap CLI tool.

This module provides timezone-aware datetime handling utilities to support
distributed teams across multiple timezones. All datetime objects should be
stored in UTC and displayed in the user's local timezone.

Key Principles:
1. Store all datetimes in UTC
2. Parse user input in their timezone, convert to UTC for storage
3. Display datetimes in user's preferred timezone
4. Maintain backward compatibility during migration
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import zoneinfo with fallback for older Python versions
try:
    from zoneinfo import ZoneInfo

    ZONEINFO_AVAILABLE = True
except ImportError:
    # Fallback for Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo

        ZONEINFO_AVAILABLE = True
    except ImportError:
        ZONEINFO_AVAILABLE = False
        # Use basic timezone handling as fallback
        from datetime import timezone as _timezone

        class ZoneInfo:
            """Minimal ZoneInfo fallback for older Python versions."""

            def __init__(self, name: str):
                self.name = name
                if name == "UTC":
                    self._tz = _timezone.utc
                else:
                    # For other timezones, we'll use UTC as fallback
                    # This is not ideal but maintains basic functionality
                    self._tz = _timezone.utc

            def __repr__(self):
                return f"ZoneInfo('{self.name}')"


class TimezoneManager:
    """Manages timezone operations for the roadmap CLI."""

    DEFAULT_TIMEZONE = "UTC"

    def __init__(self, user_timezone: str | None = None):
        """Initialize timezone manager with user's preferred timezone."""
        self.user_timezone = user_timezone or self._detect_system_timezone()
        self._validate_timezone(self.user_timezone)

    def _detect_system_timezone(self) -> str:
        """Detect the system's timezone."""
        if ZONEINFO_AVAILABLE:
            try:
                # Try to get timezone from TZ environment variable
                tz_env = os.environ.get("TZ")
                if tz_env:
                    ZoneInfo(tz_env)  # Validate it
                    return tz_env

                # Try to detect from system files (Unix-like systems)
                if sys.platform != "win32":
                    try:
                        # Check /etc/timezone (Debian/Ubuntu)
                        timezone_file = Path("/etc/timezone")
                        if timezone_file.exists():
                            tz_name = timezone_file.read_text().strip()
                            ZoneInfo(tz_name)  # Validate it
                            return tz_name
                    except (OSError, FileNotFoundError, Exception):
                        pass

                    try:
                        # Check /etc/localtime symlink (many Unix systems)
                        localtime_path = Path("/etc/localtime")
                        if localtime_path.is_symlink():
                            target = localtime_path.readlink()
                            # Extract timezone from path like /usr/share/zoneinfo/America/New_York
                            if "zoneinfo" in str(target):
                                tz_parts = str(target).split("zoneinfo/")
                                if len(tz_parts) > 1:
                                    tz_name = tz_parts[1]
                                    ZoneInfo(tz_name)  # Validate it
                                    return tz_name
                    except (OSError, Exception):
                        pass
            except Exception:
                pass

        # Fallback to UTC if detection fails
        return self.DEFAULT_TIMEZONE

    def _validate_timezone(self, tz_name: str) -> None:
        """Validate that the timezone name is valid."""
        try:
            ZoneInfo(tz_name)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{tz_name}': {e}")

    def now_utc(self) -> datetime:
        """Get current datetime in UTC with timezone information."""
        return datetime.now(timezone.utc)

    def now_local(self) -> datetime:
        """Get current datetime in user's timezone."""
        return self.now_utc().astimezone(ZoneInfo(self.user_timezone))

    def parse_user_input(
        self, date_str: str, input_timezone: str | None = None
    ) -> datetime:
        """Parse user date input and convert to UTC.

        Args:
            date_str: Date string in various formats
            input_timezone: Timezone to assume for the input (defaults to user timezone)

        Returns:
            Timezone-aware datetime in UTC
        """
        input_tz = input_timezone or self.user_timezone

        try:
            # Try to parse as ISO format first
            if "T" in date_str:
                # Handle ISO format: 2025-12-31T23:59:59
                if date_str.endswith("Z"):
                    # Already UTC
                    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                elif "+" in date_str or date_str.count("-") > 2:
                    # Has timezone info
                    return datetime.fromisoformat(date_str)
                else:
                    # No timezone info, assume user timezone
                    naive_dt = datetime.fromisoformat(date_str)
                    return naive_dt.replace(tzinfo=ZoneInfo(input_tz)).astimezone(
                        timezone.utc
                    )
            else:
                # Try to parse as date only: 2025-12-31
                if date_str.count("-") == 2:
                    naive_dt = datetime.strptime(date_str, "%Y-%m-%d")
                    return naive_dt.replace(tzinfo=ZoneInfo(input_tz)).astimezone(
                        timezone.utc
                    )

                # Try other common formats
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y/%m/%d %H:%M",
                    "%m/%d/%Y %H:%M:%S",
                    "%m/%d/%Y %H:%M",
                    "%m/%d/%Y",
                ]

                for fmt in formats:
                    try:
                        naive_dt = datetime.strptime(date_str, fmt)
                        return naive_dt.replace(tzinfo=ZoneInfo(input_tz)).astimezone(
                            timezone.utc
                        )
                    except ValueError:
                        continue

                raise ValueError(f"Unable to parse date string: {date_str}")

        except Exception as e:
            raise ValueError(f"Invalid date format '{date_str}': {e}")

    def format_for_user(self, dt: datetime, format_str: str = None) -> str:
        """Format datetime for display to user in their timezone.

        Args:
            dt: Timezone-aware datetime (preferably UTC)
            format_str: strftime format string

        Returns:
            Formatted datetime string in user's timezone
        """
        if dt.tzinfo is None:
            # Handle naive datetimes by assuming UTC
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to user's timezone
        local_dt = dt.astimezone(ZoneInfo(self.user_timezone))

        # Default format includes timezone
        if format_str is None:
            format_str = "%Y-%m-%d %H:%M:%S %Z"

        return local_dt.strftime(format_str)

    def format_relative(self, dt: datetime) -> str:
        """Format datetime as relative time (e.g., '2 hours ago', 'in 3 days').

        Args:
            dt: Timezone-aware datetime

        Returns:
            Human-readable relative time string
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        now = self.now_utc()
        diff = dt - now

        # Calculate time difference
        total_seconds = abs(diff.total_seconds())

        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = int(total_seconds // 60)
            unit = "minute" if minutes == 1 else "minutes"
            direction = "ago" if diff.total_seconds() < 0 else "from now"
            return f"{minutes} {unit} {direction}"
        elif total_seconds < 86400:  # Less than 1 day
            hours = int(total_seconds // 3600)
            unit = "hour" if hours == 1 else "hours"
            direction = "ago" if diff.total_seconds() < 0 else "from now"
            return f"{hours} {unit} {direction}"
        else:  # Days
            days = int(total_seconds // 86400)
            unit = "day" if days == 1 else "days"
            direction = "ago" if diff.total_seconds() < 0 else "from now"
            return f"{days} {unit} {direction}"

    def is_timezone_aware(self, dt: datetime) -> bool:
        """Check if datetime is timezone-aware."""
        return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

    def make_aware(self, dt: datetime, tz: str | None = None) -> datetime:
        """Convert naive datetime to timezone-aware.

        Args:
            dt: Naive datetime
            tz: Timezone to assign (defaults to user timezone)

        Returns:
            Timezone-aware datetime in UTC
        """
        if self.is_timezone_aware(dt):
            return dt.astimezone(timezone.utc)

        assumed_tz = tz or self.user_timezone
        return dt.replace(tzinfo=ZoneInfo(assumed_tz)).astimezone(timezone.utc)

    def get_common_timezones(self) -> list:
        """Get list of common timezone names."""
        if ZONEINFO_AVAILABLE:
            try:
                from zoneinfo import available_timezones

                # Return a curated list of common timezones
                common = [
                    "UTC",
                    "US/Eastern",
                    "US/Central",
                    "US/Mountain",
                    "US/Pacific",
                    "Europe/London",
                    "Europe/Paris",
                    "Europe/Berlin",
                    "Asia/Tokyo",
                    "Asia/Shanghai",
                    "Asia/Kolkata",
                    "Australia/Sydney",
                    "Australia/Melbourne",
                    "America/New_York",
                    "America/Chicago",
                    "America/Denver",
                    "America/Los_Angeles",
                    "America/Toronto",
                    "America/Mexico_City",
                    "America/Sao_Paulo",
                ]
                # Filter to only include available timezones
                available = available_timezones()
                return [tz for tz in common if tz in available]
            except ImportError:
                pass

        # Fallback list for systems without zoneinfo
        return [
            "UTC",
            "US/Eastern",
            "US/Central",
            "US/Mountain",
            "US/Pacific",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
        ]


# Global timezone manager instance
_global_timezone_manager: TimezoneManager | None = None


def get_timezone_manager(user_timezone: str | None = None) -> TimezoneManager:
    """Get or create the global timezone manager instance."""
    global _global_timezone_manager

    if _global_timezone_manager is None or user_timezone is not None:
        _global_timezone_manager = TimezoneManager(user_timezone)

    return _global_timezone_manager


def now_utc() -> datetime:
    """Convenience function to get current UTC datetime."""
    return get_timezone_manager().now_utc()


def now_local(user_timezone: str | None = None) -> datetime:
    """Convenience function to get current datetime in user's timezone."""
    return get_timezone_manager(user_timezone).now_local()


def parse_datetime(date_str: str, input_timezone: str | None = None) -> datetime:
    """Convenience function to parse user datetime input."""
    return get_timezone_manager().parse_user_input(date_str, input_timezone)


def format_datetime(
    dt: datetime, format_str: str | None = None, user_timezone: str | None = None
) -> str:
    """Convenience function to format datetime for user display."""
    return get_timezone_manager(user_timezone).format_for_user(dt, format_str)


def format_relative_time(dt: datetime, user_timezone: str | None = None) -> str:
    """Convenience function to format relative time."""
    return get_timezone_manager(user_timezone).format_relative(dt)


def migrate_naive_datetime(dt: datetime, assumed_timezone: str = "UTC") -> datetime:
    """Migrate a naive datetime to timezone-aware UTC.

    This function is used during the migration process to convert existing
    naive datetimes to timezone-aware datetimes.

    Args:
        dt: Naive datetime to migrate
        assumed_timezone: Timezone to assume for the naive datetime

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is not None:
        # Already timezone-aware, convert to UTC
        return dt.astimezone(timezone.utc)

    # Assume the specified timezone and convert to UTC
    return dt.replace(tzinfo=ZoneInfo(assumed_timezone)).astimezone(timezone.utc)


def ensure_timezone_aware(dt: datetime, assumed_timezone: str = "UTC") -> datetime:
    """Ensure a datetime is timezone-aware, converting naive datetimes as needed.

    Args:
        dt: Datetime that may be naive or timezone-aware
        assumed_timezone: Timezone to assume for naive datetimes

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is not None:
        # Already timezone-aware, convert to UTC for consistency
        return dt.astimezone(timezone.utc)

    # Naive datetime - assume specified timezone and convert to UTC
    return dt.replace(tzinfo=ZoneInfo(assumed_timezone)).astimezone(timezone.utc)
