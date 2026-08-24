"""Construction of the retained 0.1.1 collaborator graph."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from roadmap.adapters.outbound.git import SubprocessLocalGit
from roadmap.adapters.outbound.persistence import (
    CanonicalIssueUnitOfWorkFactory,
    DocumentIssueQueries,
    FilesystemWorkspaceDiagnostics,
)
from roadmap.adapters.outbound.persistence.configuration import ConfigurationFiles
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.adapters.persistence.yaml_repositories import (
    YAMLMilestoneRepository,
    YAMLProjectRepository,
)
from roadmap.application.use_cases import (
    IssueMutations,
    IssueQueries,
    LocalGit,
    Planning,
    WorkspaceHealth,
)
from roadmap.common.logging import get_logger
from roadmap.core.services import (
    IssueService,
    MilestoneService,
    ProjectService,
)
from roadmap.domain.types import Timestamp
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
from roadmap.infrastructure.coordination_gateway import CoordinationGateway
from roadmap.infrastructure.git.git_integration_ops import GitIntegrationOps
from roadmap.infrastructure.validation.vanilla_assignee_validator import (
    VanillaAssigneeValidator,
)

logger = get_logger(__name__)


class _ConfiguredCurrentIdentity:
    """Current identity resolved once from user configuration by Bootstrap."""

    def __init__(self, configured_name: str | None, local_git: SubprocessLocalGit):
        git_name, _git_email = local_git.user_identity()
        self._identity = configured_name or git_name

    def current_identity(self) -> str | None:
        return self._identity


class _SystemClock:
    def now(self) -> Timestamp:
        return Timestamp(datetime.now(UTC))


class _LocalAssigneeDirectory:
    """Provider-independent local assignee normalization."""

    def __init__(self, validator: VanillaAssigneeValidator):
        self._validator = validator

    def canonical_assignee(self, assignee: str) -> str | None:
        valid, _message = self._validator.validate(assignee)
        if not valid:
            return None
        return self._validator.get_canonical_assignee(assignee)


def wire_legacy_core(core: RoadmapCore) -> None:
    """Install the existing concrete collaborators on a compatibility facade."""
    user_config_path = Path.home() / ".config" / "roadmap" / "config.yaml"
    core.configuration = ConfigurationFiles(core.config_file, user_config_path)
    core.resolved_configuration = core.configuration.resolve()
    core._git = CoordinationGateway.get_git_integration()
    core._git.root_path = core.root_path
    core.db = CoordinationGateway.get_state_manager(db_path=core.db_dir / "state.db")
    issue_repository = CoordinationGateway.get_yaml_issue_repository(
        db=core.db, issues_dir=core.issues_dir
    )
    milestone_repository = YAMLMilestoneRepository(core.db, core.milestones_dir)
    project_repository = YAMLProjectRepository(core.db, core.projects_dir)
    core.issue_service = IssueService(issue_repository)
    core.milestone_service = MilestoneService(
        milestone_repository,
        issue_repository=issue_repository,
        issues_dir=core.issues_dir,
        milestones_dir=core.milestones_dir,
    )
    core.project_service = ProjectService(project_repository, core.milestones_dir)
    core._init_manager = InitializationManager(core.root_path, core.roadmap_dir_name)

    issue_ops = IssueOperations(core.issue_service, core.issues_dir)
    milestone_ops = MilestoneOperations(core.milestone_service)
    project_ops = ProjectOperations(core.project_service)
    assignees = VanillaAssigneeValidator()
    git_ops = GitIntegrationOps(core._git, core)
    core.issues = IssueCoordinator(issue_ops, core=core)
    core.milestones = MilestoneCoordinator(
        milestone_ops, core.milestones_dir, core=core
    )
    core.projects = ProjectCoordinator(project_ops, core=core)
    core.git = GitCoordinator(git_ops, core=core)
    documents = DocumentRepository(core.roadmap_dir)
    projection = SQLiteProjection(core.db_dir / "projection.db", documents)
    local_git_adapter = SubprocessLocalGit(core.root_path)
    identity = _ConfiguredCurrentIdentity(
        core.resolved_configuration.user.name, local_git_adapter
    )
    issue_queries = IssueQueries(
        DocumentIssueQueries(documents, projection), identity, _SystemClock()
    )
    issue_mutations = IssueMutations(
        CanonicalIssueUnitOfWorkFactory(documents, projection),
        identity,
        _LocalAssigneeDirectory(assignees),
        _SystemClock(),
    )
    dynamic_core: Any = core
    dynamic_core.issue_queries = issue_queries
    dynamic_core.issue_mutations = issue_mutations
    dynamic_core.current_identity = identity
    dynamic_core.local_git = LocalGit(local_git_adapter, issue_queries, issue_mutations)
    dynamic_core.planning = Planning(
        CanonicalIssueUnitOfWorkFactory(documents, projection), _SystemClock()
    )
    dynamic_core.health = WorkspaceHealth(
        FilesystemWorkspaceDiagnostics(documents, projection)
    )
    core._console_factory = Console


def create_core(root_path: Path, roadmap_dir_name: str = ".roadmap") -> RoadmapCore:
    """Construct the retained facade through the sole composition root."""
    return RoadmapCore(
        root_path=root_path,
        roadmap_dir_name=roadmap_dir_name,
        component_builder=wire_legacy_core,
    )


def find_existing_core(
    root_path: Path | None = None,
) -> RoadmapCore | None:
    """Discover a retained workspace and construct its facade through Bootstrap."""
    manager = InitializationManager.find_existing_roadmap(root_path)
    if manager is None:
        return None
    return create_core(manager.root_path, manager.roadmap_dir_name)
