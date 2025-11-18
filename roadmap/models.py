"""
DEPRECATED: Models module - maintained for backward compatibility.

New code should import directly from roadmap.domain:
- from roadmap.domain import Issue, Milestone, Comment, etc.

This module will be removed in v2.0.
"""

# Re-export from new locations for compatibility
from roadmap.domain import (
    Comment,
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Project,
    ProjectStatus,
    RiskLevel,
    Status,
)

__all__ = [
    "Issue",
    "IssueType",
    "Milestone",
    "MilestoneStatus",
    "Priority",
    "Project",
    "ProjectStatus",
    "RiskLevel",
    "Status",
    "Comment",
]
