"""
Persistence Layer - Data Serialization and Storage

This layer handles reading and writing data to files, including:
- YAML frontmatter parsing
- File locking mechanisms
- Enhanced persistence with backup/recovery

Modules:
- parser.py: Issue/Milestone/Project YAML frontmatter parsing
- persistence.py: Enhanced YAML validation and recovery
- file_locking.py: File-based locking mechanism
"""

from .parser import FrontmatterParser, IssueParser, MilestoneParser, ProjectParser
from .persistence import enhanced_persistence

__all__ = [
    "FrontmatterParser",
    "IssueParser",
    "MilestoneParser",
    "ProjectParser",
    "enhanced_persistence",
]
