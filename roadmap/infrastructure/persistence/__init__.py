"""
Persistence Layer - Data Serialization and Storage

This layer handles reading and writing data to files, including:
- YAML frontmatter parsing
- File locking mechanisms
- Enhanced persistence with backup/recovery
- Database infrastructure management

Modules:
- database_manager.py: SQLite connection and schema management
- parser.py: Issue/Milestone/Project YAML frontmatter parsing
- persistence.py: Enhanced YAML validation and recovery
- file_locking.py: File-based locking mechanism
"""

from .database_manager import DatabaseManager
from .parser import FrontmatterParser, IssueParser, MilestoneParser, ProjectParser
from .persistence import enhanced_persistence

__all__ = [
    "DatabaseManager",
    "FrontmatterParser",
    "IssueParser",
    "MilestoneParser",
    "ProjectParser",
    "enhanced_persistence",
]
