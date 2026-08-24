"""Compatibility facade over collaborators assembled by Bootstrap."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from roadmap.common.logging import get_logger
from roadmap.common.utils.path_utils import build_roadmap_paths

logger = get_logger(__name__)


class RoadmapCore:
    """Legacy coordination API whose concrete graph is owned by Bootstrap."""

    _git = db = milestone_service = project_service = _init_manager = issues = milestones = projects = git = planning = issue_queries = issue_mutations = configuration = resolved_configuration = _console_factory = local_git = health = current_identity = cast(Any, None)  # fmt: skip
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
