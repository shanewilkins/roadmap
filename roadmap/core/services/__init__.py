"""Service layer - Business logic orchestrators.

Services implement core business logic and workflows.
Each service focuses on one domain entity (Issue, Milestone, Project).

Services depend on:
- Domain models (Issue, Milestone, Project)
- Adapters (database, storage, parsers)

Services are used by:
- Infrastructure core (core.py orchestrator)
- CLI layer (command implementations)

Module structure after Phase 5 Stage 2 refactoring:
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
"""

from typing import TYPE_CHECKING

from .baseline.baseline_retriever import BaselineRetriever
from .baseline.baseline_selector import BaselineStrategy
from .baseline.baseline_state_retriever import BaselineStateRetriever
from .baseline.optimized_baseline_builder import OptimizedBaselineBuilder
from .comment.comment_service import CommentService
from .github.github_change_detector import GitHubChangeDetector  # noqa: F401
from .github.github_config_validator import GitHubConfigValidator  # noqa: F401
from .github.github_conflict_detector import GitHubConflictDetector  # noqa: F401
from .github.github_entity_classifier import GitHubEntityClassifier  # noqa: F401
from .github.github_integration_service import GitHubIntegrationService  # noqa: F401
from .github.github_issue_client import GitHubIssueClient  # noqa: F401
from .health.backup_cleanup_service import BackupCleanupService  # noqa: F401
from .health.entity_health_scanner import EntityHealthScanner  # noqa: F401
from .health.file_repair_service import (  # noqa: F401
    FileRepairResult,
    FileRepairService,
)
from .health.issue_health_scanner import IssueHealthScanner  # noqa: F401
from .issue.issue_creation_service import IssueCreationService  # noqa: F401
from .issue.issue_filter_service import (
    IssueFilterValidator,  # noqa: F401
    IssueQueryService,  # noqa: F401
    WorkloadCalculator,  # noqa: F401
)
from .issue.issue_matching_service import IssueMatchingService  # noqa: F401
from .issue.issue_service import IssueService  # noqa: F401
from .issue.issue_update_service import IssueUpdateService  # noqa: F401
from .issue.start_issue_service import StartIssueService  # noqa: F401
from .milestone_service import MilestoneService  # noqa: F401
from .status_change_service import (
    extract_issue_status_update,  # noqa: F401
    extract_milestone_status_update,  # noqa: F401
    parse_status_change,  # noqa: F401
)
from .utils.configuration_service import ConfigurationService  # noqa: F401
from .utils.critical_path_calculator import (  # noqa: F401
    CriticalPathCalculator,
    CriticalPathResult,
)
from .utils.dependency_analyzer import (  # noqa: F401
    DependencyAnalysisResult,
    DependencyAnalyzer,
)
from .utils.field_conflict_detector import FieldConflictDetector  # noqa: F401
from .utils.remote_fetcher import RemoteFetcher  # noqa: F401
from .utils.remote_state_normalizer import RemoteStateNormalizer  # noqa: F401
from .utils.retry_policy import RetryPolicy  # noqa: F401

# Import circular-dependency services only for type checking
# These are loaded normally at runtime but import RoadmapCore indirectly
if TYPE_CHECKING:
    from .git.git_hook_auto_sync_service import (  # noqa: F401
        GitHookAutoSyncConfig,
        GitHookAutoSyncService,
    )
    from .health.data_integrity_validator_service import (  # noqa: F401
        DataIntegrityValidatorService,
    )
    from .health.health_check_service import HealthCheckService  # noqa: F401
    from .health.infrastructure_validator_service import (
        InfrastructureValidator,  # noqa: F401
    )
    from .project.project_service import ProjectService  # noqa: F401
    from .project.project_status_service import ProjectStatusService  # noqa: F401
    from .sync.sync_change_computer import (  # noqa: F401
        compute_changes,
        compute_changes_remote,
    )
    from .sync.sync_conflict_detector import detect_field_conflicts  # noqa: F401
    from .sync.sync_conflict_resolver import (  # noqa: F401
        Conflict,
        ConflictField,
        SyncConflictResolver,
    )
    from .sync.sync_key_normalizer import normalize_remote_keys  # noqa: F401
    from .sync.sync_metadata_service import (  # noqa: F401
        SyncMetadata,
        SyncMetadataService,
        SyncRecord,
    )
    from .sync.sync_plan import (  # noqa: F401
        CreateLocalAction,
        LinkAction,
        PullAction,
        PushAction,
        ResolveConflictAction,
        SyncPlan,
        UpdateBaselineAction,
    )
    from .sync.sync_plan_executor import SyncPlanExecutor  # noqa: F401
    from .sync.sync_report import IssueChange, SyncReport  # noqa: F401
    from .sync.sync_state_comparator import SyncStateComparator  # noqa: F401
    from .sync.sync_state_manager import SyncStateManager  # noqa: F401


def __getattr__(name: str):  # noqa: ANN001, ANN201
    """Lazy load services that have circular dependencies with infrastructure.

    These services are imported only at runtime when accessed, not at module load time.
    This breaks the circular dependency: infrastructure.core → core.services → services.xxx → infrastructure.core
    """
    # Lazy modules mapping for runtime loading
    _lazy_modules = {
        "GitHookAutoSyncService": (
            "roadmap.core.services.git.git_hook_auto_sync_service",
            "GitHookAutoSyncService",
        ),
        "GitHookAutoSyncConfig": (
            "roadmap.core.services.git.git_hook_auto_sync_service",
            "GitHookAutoSyncConfig",
        ),
        "DataIntegrityValidatorService": (
            "roadmap.core.services.health.data_integrity_validator_service",
            "DataIntegrityValidatorService",
        ),
        "HealthCheckService": (
            "roadmap.core.services.health.health_check_service",
            "HealthCheckService",
        ),
        "InfrastructureValidator": (
            "roadmap.core.services.health.infrastructure_validator_service",
            "InfrastructureValidator",
        ),
        "ProjectService": (
            "roadmap.core.services.project.project_service",
            "ProjectService",
        ),
        "ProjectStatusService": (
            "roadmap.core.services.project.project_status_service",
            "ProjectStatusService",
        ),
        "compute_changes": (
            "roadmap.core.services.sync.sync_change_computer",
            "compute_changes",
        ),
        "compute_changes_remote": (
            "roadmap.core.services.sync.sync_change_computer",
            "compute_changes_remote",
        ),
        "detect_field_conflicts": (
            "roadmap.core.services.sync.sync_conflict_detector",
            "detect_field_conflicts",
        ),
        "SyncConflictResolver": (
            "roadmap.core.services.sync.sync_conflict_resolver",
            "SyncConflictResolver",
        ),
        "Conflict": (
            "roadmap.core.services.sync.sync_conflict_resolver",
            "Conflict",
        ),
        "ConflictField": (
            "roadmap.core.services.sync.sync_conflict_resolver",
            "ConflictField",
        ),
        "normalize_remote_keys": (
            "roadmap.core.services.sync.sync_key_normalizer",
            "normalize_remote_keys",
        ),
        "SyncMetadataService": (
            "roadmap.core.services.sync.sync_metadata_service",
            "SyncMetadataService",
        ),
        "SyncRecord": (
            "roadmap.core.services.sync.sync_metadata_service",
            "SyncRecord",
        ),
        "SyncMetadata": (
            "roadmap.core.services.sync.sync_metadata_service",
            "SyncMetadata",
        ),
        "SyncPlan": (
            "roadmap.core.services.sync.sync_plan",
            "SyncPlan",
        ),
        "PushAction": (
            "roadmap.core.services.sync.sync_plan",
            "PushAction",
        ),
        "PullAction": (
            "roadmap.core.services.sync.sync_plan",
            "PullAction",
        ),
        "CreateLocalAction": (
            "roadmap.core.services.sync.sync_plan",
            "CreateLocalAction",
        ),
        "LinkAction": (
            "roadmap.core.services.sync.sync_plan",
            "LinkAction",
        ),
        "UpdateBaselineAction": (
            "roadmap.core.services.sync.sync_plan",
            "UpdateBaselineAction",
        ),
        "ResolveConflictAction": (
            "roadmap.core.services.sync.sync_plan",
            "ResolveConflictAction",
        ),
        "SyncPlanExecutor": (
            "roadmap.core.services.sync.sync_plan_executor",
            "SyncPlanExecutor",
        ),
        "SyncReport": (
            "roadmap.core.services.sync.sync_report",
            "SyncReport",
        ),
        "IssueChange": (
            "roadmap.core.services.sync.sync_report",
            "IssueChange",
        ),
        "SyncStateComparator": (
            "roadmap.core.services.sync.sync_state_comparator",
            "SyncStateComparator",
        ),
        "SyncStateManager": (
            "roadmap.core.services.sync.sync_state_manager",
            "SyncStateManager",
        ),
    }

    if name in _lazy_modules:
        module_name, class_name = _lazy_modules[name]
        import importlib

        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    # Baseline
    "BaselineRetriever",
    "BaselineStrategy",
    "BaselineStateRetriever",
    "OptimizedBaselineBuilder",
    # Comment
    "CommentService",
    # Git (lazy loaded)
    # Project
    "ProjectService",
    "ProjectStatusService",
    # Root level
    "MilestoneService",
    "extract_issue_status_update",
    "extract_milestone_status_update",
    "parse_status_change",
    # Sync
    "compute_changes",
    "compute_changes_remote",
    "detect_field_conflicts",
    "SyncConflictResolver",
    "Conflict",
    "ConflictField",
    "normalize_remote_keys",
    "SyncMetadataService",
    "SyncRecord",
    "SyncMetadata",
    "SyncPlan",
    "PushAction",
    "PullAction",
    "CreateLocalAction",
    "LinkAction",
    "UpdateBaselineAction",
    "ResolveConflictAction",
    "SyncPlanExecutor",
    "SyncReport",
    "IssueChange",
    "SyncStateComparator",
    "SyncStateManager",
    # Utils
    "ConfigurationService",
    "CriticalPathCalculator",
    "CriticalPathResult",
    "DependencyAnalyzer",
    "DependencyAnalysisResult",
    "FieldConflictDetector",
    "RemoteFetcher",
    "RemoteStateNormalizer",
    "RetryPolicy",
]
