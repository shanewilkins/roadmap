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

# Import from subdirectories
from .baseline.baseline_retriever import BaselineRetriever
from .baseline.baseline_selector import BaselineStrategy
from .baseline.baseline_state_retriever import BaselineStateRetriever
from .baseline.optimized_baseline_builder import OptimizedBaselineBuilder
from .comment.comment_service import CommentService
from .git.git_hook_auto_sync_service import (
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)
from .github.github_change_detector import GitHubChangeDetector
from .github.github_config_validator import GitHubConfigValidator
from .github.github_conflict_detector import GitHubConflictDetector
from .github.github_entity_classifier import GitHubEntityClassifier
from .github.github_integration_service import GitHubIntegrationService
from .github.github_issue_client import GitHubIssueClient
from .health.backup_cleanup_service import BackupCleanupService
from .health.data_integrity_validator_service import DataIntegrityValidatorService
from .health.entity_health_scanner import EntityHealthScanner
from .health.file_repair_service import FileRepairResult, FileRepairService
from .health.health_check_service import HealthCheckService
from .health.infrastructure_validator_service import InfrastructureValidator
from .health.issue_health_scanner import IssueHealthScanner
from .issue.issue_creation_service import IssueCreationService
from .issue.issue_filter_service import (
    IssueFilterValidator,
    IssueQueryService,
    WorkloadCalculator,
)
from .issue.issue_matching_service import IssueMatchingService
from .issue.issue_service import IssueService
from .issue.issue_update_service import IssueUpdateService
from .issue.start_issue_service import StartIssueService
from .milestone_service import MilestoneService
from .project.project_service import ProjectService
from .project.project_status_service import ProjectStatusService
from .status_change_service import (
    extract_issue_status_update,
    extract_milestone_status_update,
    parse_status_change,
)
from .sync.sync_change_computer import compute_changes, compute_changes_remote
from .sync.sync_conflict_detector import detect_field_conflicts
from .sync.sync_conflict_resolver import Conflict, ConflictField, SyncConflictResolver
from .sync.sync_key_normalizer import normalize_remote_keys
from .sync.sync_metadata_service import SyncMetadata, SyncMetadataService, SyncRecord
from .sync.sync_plan import (
    CreateLocalAction,
    LinkAction,
    PullAction,
    PushAction,
    ResolveConflictAction,
    SyncPlan,
    UpdateBaselineAction,
)
from .sync.sync_plan_executor import SyncPlanExecutor
from .sync.sync_report import IssueChange, SyncReport
from .sync.sync_state_comparator import SyncStateComparator
from .sync.sync_state_manager import SyncStateManager
from .utils.configuration_service import ConfigurationService
from .utils.critical_path_calculator import CriticalPathCalculator, CriticalPathResult
from .utils.dependency_analyzer import DependencyAnalysisResult, DependencyAnalyzer
from .utils.field_conflict_detector import FieldConflictDetector
from .utils.remote_fetcher import RemoteFetcher
from .utils.remote_state_normalizer import RemoteStateNormalizer
from .utils.retry_policy import RetryPolicy

__all__ = [
    # Baseline
    "BaselineRetriever",
    "BaselineStrategy",
    "BaselineStateRetriever",
    "OptimizedBaselineBuilder",
    # Comment
    "CommentService",
    # Git
    "GitHookAutoSyncService",
    "GitHookAutoSyncConfig",
    # GitHub
    "GitHubChangeDetector",
    "GitHubConfigValidator",
    "GitHubConflictDetector",
    "GitHubEntityClassifier",
    "GitHubIntegrationService",
    "GitHubIssueClient",
    # Health
    "BackupCleanupService",
    "DataIntegrityValidatorService",
    "EntityHealthScanner",
    "FileRepairService",
    "FileRepairResult",
    "HealthCheckService",
    "InfrastructureValidator",
    "IssueHealthScanner",
    # Issue
    "IssueCreationService",
    "IssueFilterValidator",
    "IssueQueryService",
    "WorkloadCalculator",
    "IssueMatchingService",
    "IssueService",
    "IssueUpdateService",
    "StartIssueService",
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
