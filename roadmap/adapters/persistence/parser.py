"""Backward compatibility facade for parser module.

This module provides backward compatibility by re-exporting parser classes
from the refactored parser package.

New code should import directly from:
- roadmap.adapters.persistence.parser.frontmatter
- roadmap.adapters.persistence.parser.issue
- roadmap.adapters.persistence.parser.milestone
- roadmap.adapters.persistence.parser.project
"""

import warnings

# Re-export parser classes for backward compatibility
from roadmap.adapters.persistence.parser import (
    FrontmatterParser,
    IssueParser,
    MilestoneParser,
    ProjectParser,
)

# Emit deprecation warning when this module is imported
warnings.warn(
    "The 'roadmap.adapters.persistence.parser' module is deprecated. "
    "Use 'roadmap.adapters.persistence.parser' package directly instead. "
    "This module will be removed in v1.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "FrontmatterParser",
    "IssueParser",
    "MilestoneParser",
    "ProjectParser",
]
