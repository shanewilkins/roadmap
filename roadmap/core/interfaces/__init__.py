"""Protocol definitions for dependency injection and service abstraction."""

from .assignee_validator import AssigneeValidator
from .parsers import (
    FrontmatterParserInterface,
    IssueParserInterface,
    MilestoneParserInterface,
    ProjectParserInterface,
)
from .persistence import (
    FileNotFound,
    GitHistoryError,
    PersistenceInterface,
)
from .state_managers import (
    IssueStateManager,
    MilestoneStateManager,
    ProjectStateManager,
    QueryStateManager,
)

__all__ = [
    "AssigneeValidator",
    "ProjectStateManager",
    "MilestoneStateManager",
    "IssueStateManager",
    "QueryStateManager",
    "PersistenceInterface",
    "IssueParserInterface",
    "FrontmatterParserInterface",
    "MilestoneParserInterface",
    "ProjectParserInterface",
    "FileNotFound",
    "GitHistoryError",
]
