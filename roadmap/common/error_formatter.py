"""Error formatting utilities for CLI output.

Provides consistent error message formatting for both plain and rich output modes.
"""

from roadmap.common.console import is_plain_mode
from roadmap.common.errors.exceptions import RoadmapException


def format_error_message(exc: RoadmapException | Exception) -> str:
    """Format an exception for user-friendly CLI output.

    For RoadmapException: Uses user_message with appropriate styling
    For other exceptions: Uses generic fallback message

    Args:
        exc: Exception to format

    Returns:
        Formatted error message suitable for stderr output
    """
    plain = is_plain_mode()

    if isinstance(exc, RoadmapException):
        message = exc.user_message
    else:
        message = str(exc)

    # Add prefix based on mode
    if plain:
        return f"[ERROR] {message}"
    else:
        return f"❌ {message}"


def format_warning_message(message: str) -> str:
    """Format a warning message for CLI output.

    Args:
        message: Warning message text

    Returns:
        Formatted warning message
    """
    plain = is_plain_mode()

    if plain:
        return f"[WARN] {message}"
    else:
        return f"⚠️  {message}"


def format_info_message(message: str) -> str:
    """Format an info message for CLI output.

    Args:
        message: Info message text

    Returns:
        Formatted info message
    """
    plain = is_plain_mode()

    if plain:
        return f"[INFO] {message}"
    else:
        return f"ℹ️  {message}"


def format_success_message(message: str) -> str:
    """Format a success message for CLI output.

    Args:
        message: Success message text

    Returns:
        Formatted success message
    """
    plain = is_plain_mode()

    if plain:
        return f"[OK] {message}"
    else:
        return f"✅ {message}"
