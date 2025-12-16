"""Domain layer abstract repositories.

These interfaces define contracts for data access and external integrations.
Implementations are in the infrastructure layer.

This follows the Dependency Inversion Principle:
- Core services depend on these abstractions
- Infrastructure implements these abstractions
- Services are decoupled from implementation details
"""

from .issue_repository import IssueRepository
from .milestone_repository import MilestoneRepository
from .project_repository import ProjectRepository

__all__ = [
    "IssueRepository",
    "ProjectRepository",
    "MilestoneRepository",
]
