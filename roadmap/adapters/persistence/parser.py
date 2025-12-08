"""Backward compatibility facade for parser module.

This module provides backward compatibility by re-exporting parser classes
from the refactored locations within the adapters package.

New code should import directly from:
- roadmap.adapters.persistence.frontmatter_parser
- roadmap.adapters.persistence.issue_parser
- roadmap.adapters.persistence.milestone_parser
- roadmap.adapters.persistence.project_parser
"""

# Re-export parser classes for backward compatibility
from roadmap.adapters.persistence.frontmatter_parser import FrontmatterParser
from roadmap.adapters.persistence.issue_parser import IssueParser
from roadmap.adapters.persistence.milestone_parser import MilestoneParser
from roadmap.adapters.persistence.project_parser import ProjectParser

__all__ = [
    "FrontmatterParser",
    "IssueParser",
    "MilestoneParser",
    "ProjectParser",
]
