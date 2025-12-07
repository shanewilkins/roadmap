"""DEPRECATED: Backward compatibility facade for logging decorators.

Use roadmap.infrastructure.logging instead.
"""

from roadmap.infrastructure.logging import (
    get_current_user,
    log_command,
    verbose_output,
)

__all__ = ["log_command", "verbose_output", "get_current_user"]
