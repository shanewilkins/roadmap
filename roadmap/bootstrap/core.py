"""Construction of the retained 0.1.1 collaborator graph."""

from pathlib import Path
from typing import Any

from rich.console import Console

from roadmap.adapters.persistence.yaml_repositories import (
    YAMLMilestoneRepository,
    YAMLProjectRepository,
)
from roadmap.common.configuration import ConfigManager
from roadmap.common.logging import get_logger
from roadmap.core.services import (
    ConfigurationService,
    GitHubIntegrationService,
    IssueService,
    MilestoneService,
    ProjectService,
)
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
from roadmap.infrastructure.coordination_gateway import CoordinationGateway
from roadmap.infrastructure.git.git_integration_ops import GitIntegrationOps
from roadmap.infrastructure.validation.github_assignee_validator import (
    GitHubAssigneeValidator,
)
from roadmap.infrastructure.validation.vanilla_assignee_validator import (
    VanillaAssigneeValidator,
)

logger = get_logger(__name__)


def _assignee_validator(core: RoadmapCore) -> Any:
    """Select the retained validator from configuration at construction time."""
    try:
        config = ConfigManager(core.config_file).load()
        sync_backend = config.github.sync_backend if config.github else "git"
    except Exception:
        sync_backend = "git"
    if str(sync_backend).lower() == "github":
        return GitHubAssigneeValidator(core.github_service)
    return VanillaAssigneeValidator()


def wire_legacy_core(core: RoadmapCore) -> None:
    """Install the existing concrete collaborators on a compatibility facade."""
    core._git = CoordinationGateway.get_git_integration()
    core._git.root_path = core.root_path
    core.db = CoordinationGateway.get_state_manager(db_path=core.db_dir / "state.db")
    core.git_sync_monitor = CoordinationGateway.get_git_sync_monitor()
    core.git_sync_monitor.repo_path = core.root_path
    core.git_sync_monitor.state_manager = core.db
    try:
        core.db.initialize_remote_links(core.root_path)
    except Exception as error:
        logger.warning(
            "failed_to_initialize_remote_links_in_core",
            error=str(error),
            severity="operational",
        )
    core.db._git_sync_monitor = core.git_sync_monitor

    core.github_service = GitHubIntegrationService(
        root_path=core.root_path, config_file=core.config_file
    )
    core.config_service = ConfigurationService()
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
    user_ops = UserOperations(
        core.github_service, core.issue_service, _assignee_validator(core)
    )
    git_ops = GitIntegrationOps(core._git, core)
    core.issues = IssueCoordinator(issue_ops, core=core)
    core.milestones = MilestoneCoordinator(
        milestone_ops, core.milestones_dir, core=core
    )
    core.projects = ProjectCoordinator(project_ops, core=core)
    core.team = TeamCoordinator(user_ops, core=core)
    core.git = GitCoordinator(git_ops, core=core)
    core.validation = ValidationCoordinator(core.github_service, core=core)
    core._console_factory = Console
    core._git_hook_manager_factory = lambda: CoordinationGateway.get_git_hook_manager(
        core
    )


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
