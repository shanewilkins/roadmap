"""RoadmapCore - Lightweight Service Container and Coordinator

RoadmapCore is a lightweight facade that provides a clean, domain-organized
API by coordinating across multiple specialized domain coordinators.

Instead of being a god object with 50+ methods, RoadmapCore now delegates
to focused domain coordinators:
- IssueCoordinator: Issue CRUD and queries
- MilestoneCoordinator: Milestone CRUD and consistency validation
- ProjectCoordinator: Project CRUD and management
- TeamCoordinator: Team member and user management
- GitCoordinator: Git integration and branch linking
- ValidationCoordinator: Validation and configuration

This design:
- Keeps RoadmapCore <200 LOC (down from 670 LOC)
- Makes each domain independently testable
- Provides a clear mental model for users
- Scales well for future features
"""

from pathlib import Path

from roadmap.adapters.git.git import GitIntegration
from roadmap.adapters.persistence.storage import StateManager
from roadmap.core.services import (
    ConfigurationService,
    GitHubIntegrationService,
    IssueService,
    MilestoneService,
    ProjectService,
)
from roadmap.infrastructure.git_coordinator import GitCoordinator
from roadmap.infrastructure.git_integration_ops import GitIntegrationOps
from roadmap.infrastructure.initialization import InitializationManager
from roadmap.infrastructure.issue_coordinator import IssueCoordinator
from roadmap.infrastructure.issue_operations import IssueOperations
from roadmap.infrastructure.milestone_coordinator import MilestoneCoordinator
from roadmap.infrastructure.milestone_operations import MilestoneOperations
from roadmap.infrastructure.project_coordinator import ProjectCoordinator
from roadmap.infrastructure.project_operations import ProjectOperations
from roadmap.infrastructure.team_coordinator import TeamCoordinator
from roadmap.infrastructure.user_operations import UserOperations
from roadmap.infrastructure.validation_coordinator import ValidationCoordinator


class RoadmapCore:
    """Lightweight service container and coordinator of domain coordinators.

    RoadmapCore provides a clean, organized API by delegating to focused
    domain coordinators for each concern (issues, milestones, projects, etc).

    Usage:
        core = RoadmapCore()
        core.initialize()  # One-time setup

        # Use domain-specific coordinators
        issue = core.issues.create(title="...")
        milestone = core.milestones.create(name="...")
        members = core.team.get_members()
        commits = core.git.get_commits_for_issue("issue-123")
    """

    def __init__(
        self, root_path: Path | None = None, roadmap_dir_name: str = ".roadmap"
    ):
        """Initialize RoadmapCore with service setup and coordinators.

        Args:
            root_path: Root path for the roadmap (defaults to cwd)
            roadmap_dir_name: Name of the roadmap directory (defaults to .roadmap)
        """
        self.root_path = root_path or Path.cwd()
        self.roadmap_dir_name = roadmap_dir_name
        self.roadmap_dir = self.root_path / roadmap_dir_name
        self.issues_dir = self.roadmap_dir / "issues"
        self.milestones_dir = self.roadmap_dir / "milestones"
        self.projects_dir = self.roadmap_dir / "projects"
        self.templates_dir = self.roadmap_dir / "templates"
        self.artifacts_dir = self.roadmap_dir / "artifacts"
        self.config_file = self.roadmap_dir / "config.yaml"
        self.db_dir = self.roadmap_dir / "db"

        # Initialize core infrastructure
        self._git = GitIntegration(self.root_path)
        self.db = StateManager(self.db_dir / "state.db")
        self.github_service = GitHubIntegrationService(
            root_path=self.root_path, config_file=self.config_file
        )
        self.config_service = ConfigurationService()

        # Initialize services
        self.issue_service = IssueService(self.db, self.issues_dir)
        self.milestone_service = MilestoneService(
            self.db, self.milestones_dir, self.issues_dir
        )
        self.project_service = ProjectService(
            self.db, self.projects_dir, self.milestones_dir
        )

        # Initialize operations managers
        issue_ops = IssueOperations(self.issue_service, self.issues_dir)
        milestone_ops = MilestoneOperations(self.milestone_service)
        project_ops = ProjectOperations(self.project_service)
        user_ops = UserOperations(self.github_service, self.issue_service)
        git_ops = GitIntegrationOps(self._git, self)

        # Initialize domain coordinators
        self.issues = IssueCoordinator(issue_ops)
        self.milestones = MilestoneCoordinator(milestone_ops, self.milestones_dir)
        self.projects = ProjectCoordinator(project_ops)
        self.team = TeamCoordinator(user_ops)
        self.git = GitCoordinator(git_ops)
        self.validation = ValidationCoordinator(self.github_service)

        # Keep reference to init manager for setup
        self._init_manager = InitializationManager(
            self.root_path, self.roadmap_dir_name
        )

    def is_initialized(self) -> bool:
        """Check if roadmap is initialized in current directory."""
        return self._init_manager.is_initialized()

    @classmethod
    def find_existing_roadmap(
        cls, root_path: Path | None = None
    ) -> "RoadmapCore | None":
        """Find an existing roadmap directory in the current path.

        Searches for common roadmap directory names and returns a RoadmapCore
        instance if found, or None if no roadmap is detected.
        """
        manager = InitializationManager.find_existing_roadmap(root_path)
        if manager:
            return cls(
                root_path=manager.root_path, roadmap_dir_name=manager.roadmap_dir_name
            )
        return None

    def initialize(self) -> None:
        """Initialize a new roadmap in the current directory."""
        self._init_manager.initialize()

    def ensure_database_synced(
        self, force_rebuild: bool = False, show_progress: bool = True
    ) -> None:
        """Ensure database is synced with .roadmap/ files.

        This is called automatically on CLI startup to keep SQLite in sync with git files.

        Args:
            force_rebuild: Force a full rebuild even if database exists
            show_progress: Show progress indicators during sync
        """
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn

        console = Console()

        if not self.is_initialized():
            return

        first_time_setup = not self.db.database_exists()

        if first_time_setup or force_rebuild:
            if show_progress:
                with Progress(
                    SpinnerColumn(),
                    TextColumn(
                        "[bold blue]Initializing database from .roadmap/ files..."
                    ),
                    transient=True,
                ) as progress:
                    progress.add_task("sync", total=None)
                    sync_result = self.db.smart_sync()
            else:
                sync_result = self.db.smart_sync()

            if show_progress and sync_result:
                files_synced = sync_result.get("files_synced", 0)
                total_files = sync_result.get("total_files", 0)
                console.print(
                    f"✅ Database initialized: {files_synced}/{total_files} files synced"
                )

            if first_time_setup and self._git.is_git_repository():
                self._ensure_git_hooks_installed(console, show_progress)

        else:
            if self.db.has_file_changes():
                if show_progress:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn(
                            "[bold green]Updating database with recent changes..."
                        ),
                        transient=True,
                    ) as progress:
                        progress.add_task("sync", total=None)
                        sync_result = self.db.smart_sync()
                else:
                    sync_result = self.db.smart_sync()

                if show_progress and sync_result:
                    files_synced = sync_result.get("files_synced", 0)
                    console.print(f"✅ Database updated: {files_synced} files synced")

    def _ensure_git_hooks_installed(self, console, show_progress: bool = True) -> None:
        """Ensure git hooks are installed for automatic sync."""
        try:
            from roadmap.infrastructure.git_hooks import GitHookManager

            hook_manager = GitHookManager(self)

            if show_progress:
                console.print("[dim]Installing git hooks for automatic sync...[/dim]")

            success = hook_manager.install_hooks()

            if show_progress:
                if success:
                    console.print("✅ Git hooks installed successfully")
                else:
                    console.print("[yellow]⚠️  Git hooks installation failed[/yellow]")

        except Exception as e:
            if show_progress:
                console.print(f"[yellow]⚠️  Git hooks setup failed: {e}[/yellow]")

    # ========== BACKWARD COMPATIBILITY WRAPPERS ==========
    # These methods delegate to domain coordinators for backward compatibility
    # New code should use: core.issues.method(), core.milestones.method(), etc.

    def load_config(self):
        """Load roadmap configuration."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        import yaml

        with open(self.config_file) as f:
            config_data = yaml.safe_load(f) or {}

        class ConfigObject:
            def __init__(self, data):
                self.__dict__.update(data)

        return ConfigObject(config_data)











