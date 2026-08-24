"""Compatibility facade over collaborators assembled by Bootstrap."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from roadmap.common.logging import get_logger
from roadmap.common.utils.path_utils import build_roadmap_paths

logger = get_logger(__name__)


class RoadmapCore:
    """Legacy coordination API whose concrete graph is owned by Bootstrap."""

    _git = db = git_sync_monitor = github_service = milestone_service = project_service = _init_manager = issues = milestones = projects = team = git = validation = planning = issue_queries = issue_mutations = configuration = resolved_configuration = _console_factory = _git_hook_manager_factory = cast(Any, None)  # fmt: skip
    issue_service: Any = None

    def __init__(
        self,
        root_path: Path | None = None,
        roadmap_dir_name: str = ".roadmap",
        *,
        component_builder: Callable[["RoadmapCore"], None] | None = None,
    ) -> None:
        """Build paths, then let Bootstrap install the legacy collaborators."""
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

        if component_builder is None:
            from roadmap.bootstrap.core import wire_legacy_core

            component_builder = wire_legacy_core
        component_builder(self)

    def is_initialized(self) -> bool:
        """Check if roadmap is initialized in current directory."""
        return self._init_manager.is_initialized()

    def _check_initialized(self) -> None:
        """Check that roadmap is initialized and raise if not."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

    @classmethod
    def find_existing_roadmap(
        cls, root_path: Path | None = None
    ) -> "RoadmapCore | None":
        """Find an existing roadmap directory in the current path.

        Searches for common roadmap directory names and returns a RoadmapCore
        instance if found, or None if no roadmap is detected.
        """
        from roadmap.bootstrap.core import find_existing_core

        return find_existing_core(root_path)

    def initialize(self) -> None:
        """Initialize a new roadmap in the current directory."""
        self._init_manager.initialize()

    def close(self) -> None:
        """Close any database resources held by this core."""
        try:
            self.db.close()
        except Exception as e:
            logger.warning(
                "core_close_failed", error=str(e), error_type=type(e).__name__
            )

    def __enter__(self) -> "RoadmapCore":
        """Enter context manager and return self."""
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        """Exit context manager and close resources."""
        self.close()

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
        console = self._console_factory()

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
            hook_manager = self._git_hook_manager_factory()

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
