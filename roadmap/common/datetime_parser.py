"""
Unified DateTime Parser for Roadmap CLI

This module provides a single source of truth for all datetime parsing operations
across the roadmap CLI, eliminating duplication and ensuring consistent behavior.
"""

import re
from datetime import UTC, datetime
from typing import Any

# Import timezone utilities
from .utils.timezone_utils import (
    ensure_timezone_aware,
    get_timezone_manager,
)


class UnifiedDateTimeParser:
    """Single source of truth for all datetime parsing in roadmap CLI."""

    # Common datetime format patterns for parsing
    DATETIME_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]

    @classmethod
    def _handle_datetime_object(
        cls, value: datetime, assumed_timezone: str | None
    ) -> datetime:
        """Handle datetime object input (ensure timezone awareness).

        Args:
            value: Datetime object
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Timezone-aware datetime in UTC
        """
        return ensure_timezone_aware(value, assumed_timezone or "UTC")

    @classmethod
    def _normalize_string_value(cls, value: str) -> str | None:
        """Normalize string input for parsing.

        Args:
            value: String value to normalize

        Returns:
            Normalized string or None if empty
        """
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        return value if value else None

    @classmethod
    def _route_to_specialized_parser(
        cls, value: str, source_type: str, assumed_timezone: str | None
    ) -> datetime | None:
        """Route value to appropriate specialized parser based on type and format.

        Args:
            value: String value to parse
            source_type: Hint for parsing behavior
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Parsed datetime or None
        """
        if source_type == "github" or cls._is_github_format(value):
            return cls.parse_github_timestamp(value)
        elif source_type == "iso" or cls._is_iso_format(value):
            return cls.parse_iso_datetime(value, assumed_timezone)
        elif source_type == "file":
            return cls.parse_file_datetime(value, assumed_timezone)
        else:
            return cls.parse_user_datetime(value, assumed_timezone)

    @classmethod
    def parse_any_datetime(
        cls, value: Any, source_type: str = "user", assumed_timezone: str | None = None
    ) -> datetime | None:
        """Universal datetime parser for all roadmap CLI needs.

        This is the primary entry point for datetime parsing. It handles:
        - String datetime values in various formats
        - Existing datetime objects (ensures timezone awareness)
        - None values (returns None)
        - GitHub API timestamps (Z suffix)
        - File frontmatter datetimes
        - User input in multiple formats

        Args:
            value: Any datetime-like value (string, datetime, None)
            source_type: Hint for parsing behavior ("user", "github", "file", "iso")
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Timezone-aware datetime in UTC, or None if value is None/invalid
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return cls._handle_datetime_object(value, assumed_timezone)

        # Normalize string value
        normalized = cls._normalize_string_value(value)
        if not normalized:
            return None

        # Route to specialized parser
        return cls._route_to_specialized_parser(
            normalized, source_type, assumed_timezone
        )

    @classmethod
    def parse_github_timestamp(cls, github_timestamp: str) -> datetime:
        """Specialized GitHub API timestamp parsing.

        Handles GitHub's ISO format timestamps which typically end with 'Z' (UTC).
        Also handles malformed test timestamps with mixed timezone formats.

        Args:
            github_timestamp: GitHub API timestamp string

        Returns:
            Timezone-aware datetime in UTC

        Raises:
            ValueError: If timestamp cannot be parsed
        """
        if not github_timestamp:
            return datetime.min.replace(tzinfo=UTC)

        # Handle malformed timestamps from tests (e.g., "2025-01-01T00:00:00+00:00Z")
        if github_timestamp.endswith("Z") and "+00:00" in github_timestamp:
            # Remove the trailing Z if there's already timezone info
            github_timestamp = github_timestamp[:-1]
        elif github_timestamp.endswith("Z"):
            # Standard GitHub API format: replace Z with +00:00
            github_timestamp = github_timestamp.replace("Z", "+00:00")

        try:
            # Parse the timestamp and ensure it's in UTC
            dt = datetime.fromisoformat(github_timestamp)
            return ensure_timezone_aware(dt, "UTC")
        except ValueError as e:
            raise ValueError(
                f"Invalid GitHub timestamp format: {github_timestamp}"
            ) from e

    @classmethod
    def parse_file_datetime(
        cls, value: str, assumed_timezone: str | None = None
    ) -> datetime | None:
        """Parse datetime from markdown frontmatter or file content.

        Args:
            value: Datetime string from file
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Timezone-aware datetime in UTC, or None if invalid
        """
        if not value or not isinstance(value, str):
            return None

        value = value.strip()
        if not value:
            return None

        # Try ISO format first (most common in files)
        if cls._is_iso_format(value):
            return cls.parse_iso_datetime(value, assumed_timezone)

        # Try other common formats
        return cls._parse_with_formats(value, cls.DATETIME_FORMATS, assumed_timezone)

    @classmethod
    def parse_user_datetime(
        cls, value: str, assumed_timezone: str | None = None
    ) -> datetime | None:
        """Parse datetime from user input with flexible format support.

        Args:
            value: User input datetime string
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Timezone-aware datetime in UTC, or None if invalid
        """
        if not value or not isinstance(value, str):
            return None

        # Use the TimezoneManager for user input parsing
        try:
            timezone_manager = get_timezone_manager()
            return timezone_manager.parse_user_input(value, assumed_timezone)
        except Exception:
            # Fallback to manual parsing
            return cls._parse_with_formats(
                value, cls.DATETIME_FORMATS, assumed_timezone
            )

    @classmethod
    def parse_iso_datetime(
        cls, value: str, assumed_timezone: str | None = None
    ) -> datetime | None:
        """Parse ISO format datetime string.

        Args:
            value: ISO format datetime string
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Timezone-aware datetime in UTC, or None if invalid
        """
        if not value:
            return None

        try:
            # Handle Z suffix (UTC indicator)
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")

            # Parse with fromisoformat
            dt = datetime.fromisoformat(value)
            return ensure_timezone_aware(dt, assumed_timezone or "UTC")

        except ValueError:
            return None

    @classmethod
    def _is_github_format(cls, value: str) -> bool:
        """Check if string looks like a GitHub API timestamp."""
        return value.endswith("Z") or (
            "T" in value and (":" in value) and ("+" in value or "Z" in value)
        )

    @classmethod
    def _is_iso_format(cls, value: str) -> bool:
        """Check if string looks like ISO format."""
        iso_pattern = r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
        return bool(re.match(iso_pattern, value))

    @classmethod
    def _parse_with_formats(
        cls, value: str, formats: list, assumed_timezone: str | None = None
    ) -> datetime | None:
        """Try parsing with multiple datetime formats.

        Args:
            value: Datetime string to parse
            formats: List of strptime format strings to try
            assumed_timezone: Timezone to assume for naive datetimes

        Returns:
            Timezone-aware datetime in UTC, or None if no format works
        """
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return ensure_timezone_aware(dt, assumed_timezone or "UTC")
            except ValueError:
                continue
        return None


# Convenience functions for backward compatibility and ease of use
def parse_datetime(
    value: Any, source_type: str = "user", assumed_timezone: str | None = None
) -> datetime | None:
    """Convenience function for universal datetime parsing."""
    return UnifiedDateTimeParser.parse_any_datetime(
        value, source_type, assumed_timezone
    )


def parse_github_datetime(github_timestamp: str) -> datetime:
    """Convenience function for GitHub timestamp parsing."""
    return UnifiedDateTimeParser.parse_github_timestamp(github_timestamp)


def parse_file_datetime(
    value: str, assumed_timezone: str | None = None
) -> datetime | None:
    """Convenience function for file datetime parsing."""
    return UnifiedDateTimeParser.parse_file_datetime(value, assumed_timezone)


def parse_user_datetime(
    value: str, assumed_timezone: str | None = None
) -> datetime | None:
    """Convenience function for user input datetime parsing."""
    return UnifiedDateTimeParser.parse_user_datetime(value, assumed_timezone)
