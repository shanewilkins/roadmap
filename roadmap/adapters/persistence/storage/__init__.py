"""Storage layer with modularized state management.

Organizes large query and conflict operations into separate service files:
- state_manager.py: Main StateManager facade (310 LOC)
- queries.py: Complex database queries and aggregations (190 LOC)
- conflicts.py: Git conflict detection and handling (80 LOC)
"""

from .state_manager import (
    DatabaseError,
    StateManager,
    get_state_manager,
    initialize_state_manager,
)

__all__ = [
    "DatabaseError",
    "StateManager",
    "get_state_manager",
    "initialize_state_manager",
]
