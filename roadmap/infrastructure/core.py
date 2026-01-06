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
from roadmap.adapters.persistence.yaml_repositories import YAMLIssueRepository
from roadmap.common.path_utils import build_roadmap_paths
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

        # Build all standard roadmap paths
        paths = build_roadmap_paths(self.root_path, roadmap_dir_name)
        self.roadmap_dir = paths["roadmap_dir"]
        self.issues_dir = paths["issues_dir"]
        self.milestones_dir = paths["milestones_dir"]
        self.projects_dir = paths["projects_dir"]
        self.templates_dir = paths["templates_dir"]
        self.artifacts_dir = paths["artifacts_dir"]
        self.config_file = paths["config_file"]
        self.db_dir = paths["db_dir"]

        # Initialize core infrastructure
        self._git = GitIntegration(self.root_path)

        # Initialize StateManager first (without GitSyncMonitor)
        self.db = StateManager(self.db_dir / "state.db")

        # Initialize GitSyncMonitor with StateManager for database sync
        from roadmap.adapters.git.sync_monitor import GitSyncMonitor

        self.git_sync_monitor = GitSyncMonitor(
            repo_path=self.root_path, state_manager=self.db
        )

        # Wire GitSyncMonitor into StateManager for transparent cache sync
        self.db._git_sync_monitor = self.git_sync_monitor

        self.github_service = GitHubIntegrationService(
            root_path=self.root_path, config_file=self.config_file
        )
        self.config_service = ConfigurationService()

        # Initialize repositories (abstraction layer)
        from roadmap.adapters.persistence.yaml_repositories import (
            YAMLMilestoneRepository,
            YAMLProjectRepository,
        )

        issue_repository = YAMLIssueRepository(self.db, self.issues_dir)
        milestone_repository = YAMLMilestoneRepository(self.db, self.milestones_dir)
        project_repository = YAMLProjectRepository(self.db, self.projects_dir)

        # Initialize services with repository injection
        # (decoupled from implementation)
        self.issue_service = IssueService(issue_repository)
        self.milestone_service = MilestoneService(
            milestone_repository,
            issue_repository=issue_repository,
            issues_dir=self.issues_dir,
            milestones_dir=self.milestones_dir,
        )
        self.project_service = ProjectService(project_repository, self.milestones_dir)

        # Keep reference to init manager for setup (needed before creating coordinators)
        self._init_manager = InitializationManager(
            self.root_path, self.roadmap_dir_name
        )

        # Initialize operations managers
        issue_ops = IssueOperations(self.issue_service, self.issues_dir)
        milestone_ops = MilestoneOperations(self.milestone_service)
        project_ops = ProjectOperations(self.project_service)

        # Determine appropriate assignee validator based on sync backend
        assignee_validator = self._get_assignee_validator()
        user_ops = UserOperations(
            self.github_service, self.issue_service, assignee_validator
        )
        git_ops = GitIntegrationOps(self._git, self)

        # Initialize domain coordinators (pass self for initialization check)
        self.issues = IssueCoordinator(issue_ops, core=self)
        self.milestones = MilestoneCoordinator(
            milestone_ops, self.milestones_dir, core=self
        )
        self.projects = ProjectCoordinator(project_ops, core=self)
        self.team = TeamCoordinator(user_ops, core=self)
        self.git = GitCoordinator(git_ops, core=self)
        self.validation = ValidationCoordinator(self.github_service, core=self)

    def is_initialized(self) -> bool:
        """Check if roadmap is initialized in current directory."""
        return self._init_manager.is_initialized()

    def _check_initialized(self) -> None:
        """Check that roadmap is initialized and raise if not."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

    def _get_assignee_validator(self):
        """Determine the appropriate assignee validator based on sync backend.

        Returns the validator for the configured sync backend:
        - "github" backend → GitHubAssigneeValidator (validates against collaborators)
        - "git" or other backend → VanillaAssigneeValidator (accepts any assignee)

        Defaults to vanilla/git validator if no backend is configured.

        Returns:
            An assignee validator instance (implements AssigneeValidator protocol)
        """
        from roadmap.common.config_manager import ConfigManager
        from roadmap.infrastructure.github_assignee_validator import (
            GitHubAssigneeValidator,
        )
        from roadmap.infrastructure.vanilla_assignee_validator import (
            VanillaAssigneeValidator,
        )

        try:
            config_manager = ConfigManager(self.config_file)
            config = config_manager.load()
            # Access dataclass attributes, not dictionary
            sync_backend = config.github.sync_backend if config.github else "git"
        except Exception:
            # If we can't read config, default to vanilla/git validator
            sync_backend = "git"

        if str(sync_backend).lower() == "github":
            return GitHubAssigneeValidator(self.github_service)
        else:
            # Default to vanilla validator for "git" backend or if not specified
            return VanillaAssigneeValidator()

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

    def _update_gitignore(self) -> None:
        """Update .gitignore to exclude roadmap local data from version control."""
        self._init_manager._update_gitignore()

    def _sync_with_progress(self, message: str) -> dict | None:
        """Run database sync with progress display.

        Args:
            message: Progress message to display

        Returns:
            Sync result dictionary or None
        """
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]{message}..."),
            transient=True,
        ) as progress:
            progress.add_task("sync", total=None)
            return self.db.smart_sync()

    def _sync_without_progress(self) -> dict | None:
        """Run database sync without progress display.

        Returns:
            Sync result dictionary or None
        """
        return self.db.smart_sync()

    def _display_sync_result(self, console, message: str, files_synced: int) -> None:
        """Display sync result message.

        Args:
            console: Rich console instance
            message: Message to display
            files_synced: Number of files synced
        """
        console.print(f"✅ {message}: {files_synced} files synced")

    def _handle_first_time_setup(
        self, console, show_progress: bool, force_rebuild: bool
    ) -> None:
        """Handle first-time database initialization.

        Args:
            console: Rich console instance
            show_progress: Whether to show progress
            force_rebuild: Whether full rebuild was requested
        """
        if show_progress:
            sync_result = self._sync_with_progress(
                "Initializing database from .roadmap/ files"
            )
        else:
            sync_result = self._sync_without_progress()

        if show_progress and sync_result:
            files_synced = sync_result.get("files_synced", 0)
            total_files = sync_result.get("total_files", 0)
            console.print(
                f"✅ Database initialized: {files_synced}/{total_files} files synced"
            )

        if not force_rebuild and self._git.is_git_repository():
            self._ensure_git_hooks_installed(console, show_progress)

    def _handle_incremental_sync(self, console, show_progress: bool) -> None:
        """Handle incremental database sync.

        Args:
            console: Rich console instance
            show_progress: Whether to show progress
        """
        if not self.db.has_file_changes():
            return

        if show_progress:
            sync_result = self._sync_with_progress(
                "Updating database with recent changes"
            )
        else:
            sync_result = self._sync_without_progress()

        if show_progress and sync_result:
            files_synced = sync_result.get("files_synced", 0)
            self._display_sync_result(console, "Database updated", files_synced)

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

        console = Console()

        if not self.is_initialized():
            return

        first_time_setup = not self.db.database_exists()

        if first_time_setup or force_rebuild:
            self._handle_first_time_setup(console, show_progress, first_time_setup)
        else:
            self._handle_incremental_sync(console, show_progress)

    def _ensure_git_hooks_installed(self, console, show_progress: bool = True) -> None:
        """Ensure git hooks are installed for automatic sync."""
        try:
            from roadmap.adapters.git.git_hooks import GitHookManager

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

    def get_issues_by_milestone(self) -> dict[str, list]:
        """Get all issues grouped by milestone (backward compatibility wrapper)."""
        return self.issues.get_grouped_by_milestone()

    def get_next_milestone(self):
        """Get the next upcoming milestone by due date (backward compatibility wrapper)."""
        return self.milestones._ops.get_next_milestone()

    def move_issue_to_milestone(self, issue_id: str, milestone_name: str):
        """Move an issue to a specific milestone (backward compatibility wrapper)."""
        return self.issues.move_to_milestone(issue_id, milestone_name)

    def load_config(self):
        """Load roadmap configuration."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        import yaml

        with open(self.config_file) as f:
            loaded = yaml.safe_load(f)
            config_data: dict = loaded if isinstance(loaded, dict) else {}

        # Ensure all expected config sections exist
        if "milestones" not in config_data:
            config_data["milestones"] = {
                "auto_sequence": True,
                "version_format": "v{major}.{minor}.{patch}",
            }

        if "sync" not in config_data:
            config_data["sync"] = {
                "github_enabled": False,
                "auto_sync": False,
                "sync_interval_seconds": 300,
            }

        if "display" not in config_data:
            config_data["display"] = {
                "theme": "default",
                "show_progress": True,
                "compact_output": False,
            }

        class ConfigObject:
            def __init__(self, data):
                self.__dict__.update(data)

        return ConfigObject(config_data)
