"""Parser package with modularized entity-specific parsers.

Organizes parser classes across semantic modules:
- frontmatter.py: YAML frontmatter parsing and serialization (70 LOC)
- issue.py: Issue entity parsing and serialization (160 LOC)
- milestone.py: Milestone entity parsing and serialization (130 LOC)
- project.py: Project entity parsing and serialization (100 LOC)
"""

from .frontmatter import FrontmatterParser
from .issue import IssueParser
from .milestone import MilestoneParser
from .project import ProjectParser

__all__ = [
    "FrontmatterParser",
    "IssueParser",
    "MilestoneParser",
    "ProjectParser",
]
