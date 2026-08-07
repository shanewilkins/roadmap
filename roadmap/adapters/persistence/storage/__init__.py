"""Storage layer with modularized state management.

Organizes large query and conflict operations into separate service files:
- state_manager.py: Main StateManager facade (290 LOC after refactor)
- connection_manager.py: Database connection and transaction management (60 LOC)
- project_storage.py: Project CRUD operations (80 LOC)
- milestone_storage.py: Milestone CRUD operations (70 LOC)
- issue_storage.py: Issue CRUD operations (80 LOC)
- sync_state_storage.py: Sync state and file synchronization (180 LOC)
- queries.py: Complex database queries and aggregations (190 LOC)
- conflicts.py: Git conflict detection and handling (80 LOC)
"""

from .connection_manager import ConnectionManager
from .issue_storage import IssueStorage
from .milestone_storage import MilestoneStorage
from .project_storage import ProjectStorage
from .state_manager import (
    DatabaseError,
    StateManager,
    get_state_manager,
    initialize_state_manager,
)
from .sync_state_storage import SyncStateStorage

__all__ = [
    "ConnectionManager",
    "DatabaseError",
    "IssueStorage",
    "MilestoneStorage",
    "ProjectStorage",
    "StateManager",
    "SyncStateStorage",
    "get_state_manager",
    "initialize_state_manager",
]
