"""DEPRECATED: Backward compatibility facade for performance tracking.

Use roadmap.infrastructure.logging instead.
"""

from roadmap.infrastructure.logging import (
    track_database_operation,
    track_operation_time,
)

__all__ = ["track_operation_time", "track_database_operation"]
