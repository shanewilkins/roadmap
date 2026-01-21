"""
Persistence Layer - Data Serialization and Storage.

This layer handles reading and writing data to files, including:
- YAML frontmatter parsing
- File locking mechanisms
- Enhanced persistence with backup/recovery
- Database infrastructure management
- File synchronization

Modules:
- database_manager.py: SQLite connection and schema management
- file_synchronizer.py: File-to-database synchronization
- parser.py: Issue/Milestone/Project YAML frontmatter parsing
- persistence.py: Enhanced YAML validation and recovery
- file_locking.py: File-based locking mechanism
"""

from .conflict_resolver import ConflictResolver
from .database_manager import DatabaseManager
from .file_synchronizer import FileSynchronizer
from .parser import FrontmatterParser, IssueParser, MilestoneParser, ProjectParser
from .persistence import enhanced_persistence
from .sync_state_tracker import SyncStateTracker

__all__ = [
    "ConflictResolver",
    "DatabaseManager",
    "FileSynchronizer",
    "FrontmatterParser",
    "IssueParser",
    "MilestoneParser",
    "ProjectParser",
    "SyncStateTracker",
    "enhanced_persistence",
]
