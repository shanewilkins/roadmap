"""Duration and count formatting utilities."""


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_count(count: int, singular: str, plural: str | None = None) -> str:
    """Format a count with proper singular/plural form.

    Args:
        count: The count
        singular: Singular form
        plural: Plural form (defaults to singular + 's')

    Returns:
        Formatted count string
    """
    if plural is None:
        plural = f"{singular}s"
    return f"{count} {singular if count == 1 else plural}"
