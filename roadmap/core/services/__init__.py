"""Service layer - Business logic orchestrators.

Services implement core business logic and workflows.
Each service focuses on one domain entity (Issue, Milestone, Project).

Services depend on:
- Domain models (Issue, Milestone, Project)
- Adapters (database, storage, parsers)

Services are used by:
- Infrastructure core (core.py orchestrator)
- CLI layer (command implementations)

Imported from:
from roadmap.core.services import IssueService, MilestoneService, ProjectService, ConfigurationService, GitHubIntegrationService
"""

"""Service layer - Business logic orchestrators.

Services implement core business logic and workflows.
Each service focuses on one domain entity (Issue, Milestone, Project).

Services depend on:
- Domain models (Issue, Milestone, Project)
- Adapters (database, storage, parsers)

Services are used by:
- Infrastructure core (core.py orchestrator)
- CLI layer (command implementations)

Module structure:
- sync/: Synchronization orchestration and conflict resolution
- health/: Health checking, validation, and repair services
- github/: GitHub integration and API client services
- baseline/: Baseline selection and retrieval services
- issue/: Issue management and lifecycle services
- project/: Project management services
- comment/: Comment service
- git/: Git hooks and auto-sync services
- utils/: Utility and shared services
- validators/: Health validators
- helpers/: Helper functions

Note: With the Phase 5 refactoring, service modules are now organized into
subdirectories by domain. For backward compatibility, imports should use:
- from roadmap.core.services.sync import SyncPlan
- from roadmap.core.services.health import HealthCheckService
- from roadmap.core.services.github import GitHubIntegrationService
etc.

The main module is kept minimal to avoid circular import issues.
"""

# Re-export commonly used services for backward compatibility
# These are imported lazily to avoid circular imports

def __getattr__(name):
    """Lazy loading of service modules for backward compatibility."""
    # Sync services
    if name == "SyncPlan":
        from .sync.sync_plan import SyncPlan
        return SyncPlan
    elif name == "SyncReport":
        from .sync.sync_report import SyncReport
        return SyncReport
    elif name == "SyncConflictResolver":
        from .sync.sync_conflict_resolver import SyncConflictResolver
        return SyncConflictResolver
    elif name == "SyncStateManager":
        from .sync.sync_state_manager import SyncStateManager
        return SyncStateManager
    elif name == "SyncStateComparator":
        from .sync.sync_state_comparator import SyncStateComparator
        return SyncStateComparator
    
    # Health services
    elif name == "HealthCheckService":
        from .health.health_check_service import HealthCheckService
        return HealthCheckService
    elif name == "EntityHealthScanner":
        from .health.entity_health_scanner import EntityHealthScanner
        return EntityHealthScanner
    
    # GitHub services
    elif name == "GitHubIntegrationService":
        from .github.github_integration_service import GitHubIntegrationService
        return GitHubIntegrationService
    
    # Issue services
    elif name == "IssueService":
        from .issue.issue_service import IssueService
        return IssueService
    elif name == "IssueCreationService":
        from .issue.issue_creation_service import IssueCreationService
        return IssueCreationService
    elif name == "IssueUpdateService":
        from .issue.issue_update_service import IssueUpdateService
        return IssueUpdateService
    elif name == "StartIssueService":
        from .issue.start_issue_service import StartIssueService
        return StartIssueService
    elif name == "IssueQueryService":
        from .issue.issue_filter_service import IssueQueryService
        return IssueQueryService
    
    # Project services
    elif name == "ProjectService":
        from .project.project_service import ProjectService
        return ProjectService
    
    # Config
    elif name == "ConfigurationService":
        from .utils.configuration_service import ConfigurationService
        return ConfigurationService
    
    # Milestone
    elif name == "MilestoneService":
        from .milestone_service import MilestoneService
        return MilestoneService
    
    # Handle module-level imports for backward compatibility (for mocking in tests)
    # e.g., patch('roadmap.core.services.git_hook_auto_sync_service')
    elif name == "git_hook_auto_sync_service":
        from .git import git_hook_auto_sync_service
        return git_hook_auto_sync_service
    elif name == "health_check_service":
        from .health import health_check_service
        return health_check_service
    elif name == "entity_health_scanner":
        from .health import entity_health_scanner
        return entity_health_scanner
    elif name == "backup_cleanup_service":
        from .health import backup_cleanup_service
        return backup_cleanup_service
    elif name == "baseline_state_retriever":
        from .baseline import baseline_state_retriever
        return baseline_state_retriever
    elif name == "github_config_validator":
        from .github import github_config_validator
        return github_config_validator
    elif name == "infrastructure_validator_service":
        from .health import infrastructure_validator_service
        return infrastructure_validator_service
    elif name == "initialization":
        from . import initialization
        return initialization
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SyncPlan",
    "SyncReport",
    "SyncConflictResolver",
    "SyncStateManager",
    "SyncStateComparator",
    "HealthCheckService",
    "EntityHealthScanner",
    "GitHubIntegrationService",
    "IssueService",
    "IssueCreationService",
    "IssueUpdateService",
    "StartIssueService",
    "IssueQueryService",
    "ProjectService",
    "ConfigurationService",
    "MilestoneService",
]

__all__ = [
    "IssueService",
    "MilestoneService",
    "ProjectService",
    "ConfigurationService",
    "GitHubIntegrationService",
    "IssueCreationService",
    "IssueUpdateService",
    "StartIssueService",
    "IssueFilterValidator",
    "IssueQueryService",
    "WorkloadCalculator",
    "parse_status_change",
    "extract_issue_status_update",
    "extract_milestone_status_update",
]
