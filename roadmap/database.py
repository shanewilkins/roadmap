"""Database module - DEPRECATED.

DEPRECATED: This module is maintained for backward compatibility.
New code should import from roadmap.infrastructure.storage instead.

- StateManager, DatabaseError -> roadmap.infrastructure.storage
"""

# Re-export from infrastructure layer for backward compatibility
from roadmap.infrastructure.storage import DatabaseError, StateManager

__all__ = ["StateManager", "DatabaseError"]
