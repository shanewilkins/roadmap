"""Test data factories for building domain objects with fluent interfaces.

This module provides builder classes for creating test fixtures consistently
across the test suite. Builders use a fluent interface for readable, flexible
test data creation.

Example:
    >>> issue = IssueBuilder().with_title("Fix bug").with_priority(Priority.HIGH).build()
    >>> milestone = MilestoneBuilder().with_name("v1.0").with_due_date(date).build()

Benefits:
    - Single source of truth for test data creation
    - Changing test data requires updates in one place (not 150+ locations)
    - Fluent interface is readable and discoverable
    - Easy to extend with new builder methods
    - Type-safe via static type hints
"""

from .domain import CommentBuilder, IssueBuilder, MilestoneBuilder, ProjectBuilder
from .sync_issue_factory import SyncIssueFactory

__all__ = [
    "IssueBuilder",
    "MilestoneBuilder",
    "ProjectBuilder",
    "CommentBuilder",
    "SyncIssueFactory",
]
