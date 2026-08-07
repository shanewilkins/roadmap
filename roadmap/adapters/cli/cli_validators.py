"""CLI validation helpers - shared across all command modules.

This module provides reusable validation functions for common CLI patterns:
- Priority enum validation

Consolidates duplicated validation logic across commands.
"""

from roadmap.common.console import get_console

console = get_console()


# ===== Priority/Status Validation =====


def validate_priority(priority_str: str, domain_module=None):
    """Validate and convert priority string to Priority enum.

    Args:
        priority_str: Priority string (critical, high, medium, low)
        domain_module: Optional domain module for custom Priority class

    Returns:
        Priority enum if valid, None if invalid
    """
    if domain_module is None:
        from roadmap.core.domain import Priority
    else:
        Priority = domain_module.Priority

    try:
        return Priority(priority_str.upper())
    except ValueError:
        console.print(
            f"❌ Invalid priority: {priority_str}. Use: critical, high, medium, low",
            style="bold red",
        )
        return None
