"""Small, timezone-aware parser for CLI date arguments."""

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
)


def _aware(value: datetime, timezone_name: str) -> datetime:
    localized = (
        value.replace(tzinfo=ZoneInfo(timezone_name)) if value.tzinfo is None else value
    )
    return localized.astimezone(UTC)


class UnifiedDateTimeParser:
    """Parse the documented ISO, date, and local date-time forms."""

    @classmethod
    def parse_any_datetime(
        cls,
        value: Any,
        source_type: str = "user",
        assumed_timezone: str | None = None,
    ) -> datetime | None:
        del source_type
        if value is None:
            return None
        if isinstance(value, datetime):
            return _aware(value, assumed_timezone or "UTC")
        return cls.parse_user_datetime(str(value), assumed_timezone)

    @staticmethod
    def parse_user_datetime(
        value: str, assumed_timezone: str | None = None
    ) -> datetime | None:
        normalized = value.strip()
        if not normalized:
            return None
        timezone_name = assumed_timezone or "UTC"
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            for pattern in _FORMATS:
                try:
                    parsed = datetime.strptime(normalized, pattern)
                    break
                except ValueError:
                    continue
            else:
                return None
        try:
            return _aware(parsed, timezone_name)
        except (KeyError, ValueError):
            return None


def parse_user_datetime(
    value: str, assumed_timezone: str | None = None
) -> datetime | None:
    return UnifiedDateTimeParser.parse_user_datetime(value, assumed_timezone)
