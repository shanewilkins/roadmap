"""Infrastructure layer - Coordination, operations, and cross-domain concerns.

This module is organized by concern:
- coordination/: RoadmapCore, domain coordinators, and operations
- git/: Git integration and branch linking
- observability/: Health checks and monitoring
- validation/: Data validation and GitHub integration
- security/: Credential management and security concerns
- maintenance/: Cleanup and maintenance operations

Re-exports common items for backward compatibility.
"""

# Re-export from coordination for backward compatibility
from roadmap.infrastructure.coordination.core import RoadmapCore
from roadmap.infrastructure.coordination.git_coordinator import GitCoordinator
from roadmap.infrastructure.coordination.initialization import InitializationManager
from roadmap.infrastructure.coordination.issue_coordinator import IssueCoordinator
from roadmap.infrastructure.coordination.issue_operations import IssueOperations
from roadmap.infrastructure.coordination.milestone_coordinator import (
    MilestoneCoordinator,
)
from roadmap.infrastructure.coordination.milestone_operations import MilestoneOperations
from roadmap.infrastructure.coordination.project_coordinator import ProjectCoordinator
from roadmap.infrastructure.coordination.project_operations import ProjectOperations
from roadmap.infrastructure.coordination.team_coordinator import TeamCoordinator
from roadmap.infrastructure.coordination.user_operations import UserOperations
from roadmap.infrastructure.coordination.validation_coordinator import (
    ValidationCoordinator,
)

# Re-export from git for backward compatibility
from roadmap.infrastructure.git.git_integration_ops import GitIntegrationOps

# Re-export from observability for backward compatibility
from roadmap.infrastructure.observability.health import HealthCheck
from roadmap.infrastructure.observability.health_formatter import HealthStatusFormatter

__all__ = [
    "RoadmapCore",
    "GitCoordinator",
    "InitializationManager",
    "IssueCoordinator",
    "IssueOperations",
    "MilestoneCoordinator",
    "MilestoneOperations",
    "ProjectCoordinator",
    "ProjectOperations",
    "TeamCoordinator",
    "UserOperations",
    "ValidationCoordinator",
    "GitIntegrationOps",
    "HealthCheck",
    "HealthStatusFormatter",
]
