"""Application Layer Core Orchestrator - RoadmapCore

This module contains the main RoadmapCore class that orchestrates
all application layer services and provides the public API for roadmap operations.

RoadmapCore is the main entry point for the roadmap system, coordinating:
- Issue management (IssueService)
- Milestone planning (MilestoneService)
- Project tracking (ProjectService)
- Database state (StateManager)
- Git integration (GitIntegration)
- Configuration (ConfigurationService)
- Visualization (VisualizationService)

Note: This replaces the deprecated roadmap.core module.
Old code should update imports from "from roadmap.infrastructure.core import RoadmapCore"
to "from roadmap.infrastructure.core import RoadmapCore".

- RoadmapCore orchestration -> roadmap.application.core.RoadmapCore
- Issue operations -> roadmap.application.services.IssueService
- Milestone operations -> roadmap.application.services.MilestoneService
- Project operations -> roadmap.application.services.ProjectService
- GitHub integration -> roadmap.infrastructure.github.GitHubClient
- Git operations -> roadmap.infrastructure.git.GitOperations
- Storage/Database -> roadmap.infrastructure.storage.StateManager

This module will be removed in v2.0. Please migrate your code to use the
new layered architecture for better maintainability and testability.

See: docs/ARCHITECTURE.md for the new structure.
See: REFACTORING_IMPLEMENTATION_PLAN.md for migration details.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.adapters.git.git import GitIntegration
from roadmap.adapters.persistence.parser import IssueParser, MilestoneParser
from roadmap.adapters.persistence.storage import StateManager
from roadmap.core.domain import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Project,
    Status,
)
from roadmap.core.services import (
    ConfigurationService,
    GitHubIntegrationService,
    IssueService,
    MilestoneService,
    ProjectService,
)
from roadmap.infrastructure.initialization import InitializationManager
from roadmap.infrastructure.issue_operations import IssueOperations
from roadmap.infrastructure.milestone_operations import MilestoneOperations
from roadmap.infrastructure.project_operations import ProjectOperations


class RoadmapCore:
    """Core roadmap functionality."""

    def __init__(
        self, root_path: Path | None = None, roadmap_dir_name: str = ".roadmap"
    ):
        """Initialize roadmap core with root path and custom roadmap directory name."""
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

        # Initialize Git integration
        self.git = GitIntegration(self.root_path)

        # Initialize database manager
        self.db = StateManager(self.db_dir / "state.db")

        # Initialize GitHub integration service
        self.github_service = GitHubIntegrationService(
            root_path=self.root_path, config_file=self.config_file
        )

        # Initialize service layer
        self.issue_service = IssueService(self.db, self.issues_dir)
        self.milestone_service = MilestoneService(
            self.db, self.milestones_dir, self.issues_dir
        )
        self.project_service = ProjectService(
            self.db, self.projects_dir, self.milestones_dir
        )
        # visualization_service moved to future/
        self.config_service = ConfigurationService()

        # Initialize manager for setup/initialization logic
        self._init_manager = InitializationManager(
            self.root_path, self.roadmap_dir_name
        )

        # Initialize manager for issue operations
        self._issue_ops = IssueOperations(self.issue_service, self.issues_dir)

        # Initialize manager for milestone operations
        self._milestone_ops = MilestoneOperations(self.milestone_service)

        # Initialize manager for project operations
        self._project_ops = ProjectOperations(self.project_service)

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
            # If not initialized, don't auto-sync
            return

        # Install git hooks on first database initialization
        first_time_setup = not self.db.database_exists()

        # Check if database needs sync
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

            # Install git hooks on first setup
            if first_time_setup and self.git.is_git_repository():
                self._ensure_git_hooks_installed(console, show_progress)

        else:
            # Check if files have changed since last sync
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
            from ..infrastructure.git_hooks import GitHookManager

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

    def load_config(self) -> Any:
        """Load roadmap configuration.

        Note: RoadmapConfig class moved to application layer.
        This method returns a dict-like object with attribute access.
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        # Load from config.yaml file
        import yaml

        with open(self.config_file) as f:
            config_data = yaml.safe_load(f) or {}

        # Create a simple object that allows attribute access
        class ConfigObject:
            def __init__(self, data):
                self.__dict__.update(data)

        return ConfigObject(config_data)

    def create_issue(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        issue_type: IssueType = IssueType.OTHER,
        milestone: str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
        estimated_hours: float | None = None,
        depends_on: list[str] | None = None,
        blocks: list[str] | None = None,
    ) -> Issue:
        """Create a new issue."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self._issue_ops.create_issue(
            title=title,
            priority=priority,
            issue_type=issue_type,
            milestone=milestone,
            labels=labels,
            assignee=assignee,
            estimated_hours=estimated_hours,
            depends_on=depends_on,
            blocks=blocks,
        )

    def list_issues(
        self,
        milestone: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        issue_type: IssueType | None = None,
        assignee: str | None = None,
    ) -> list[Issue]:
        """List issues with optional filtering."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self._issue_ops.list_issues(
            milestone=milestone,
            status=status,
            priority=priority,
            issue_type=issue_type,
            assignee=assignee,
        )

    def get_issue(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID."""
        return self._issue_ops.get_issue(issue_id)

    def update_issue(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue."""
        return self._issue_ops.update_issue(issue_id, **updates)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue."""
        return self._issue_ops.delete_issue(issue_id)

    def create_milestone(
        self, name: str, description: str = "", due_date: datetime | None = None
    ) -> Milestone:
        """Create a new milestone."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self._milestone_ops.create_milestone(
            name=name, description=description, due_date=due_date
        )

    def list_milestones(self) -> list[Milestone]:
        """List all milestones."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self._milestone_ops.list_milestones()

    def get_milestone(self, name: str) -> Milestone | None:
        """Get a specific milestone by name (searches by YAML name field, not filename)."""
        return self._milestone_ops.get_milestone(name)

    def delete_milestone(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Name of the milestone to delete

        Returns:
            True if milestone was deleted, False if not found
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        return self._milestone_ops.delete_milestone(name)

    def update_milestone(
        self,
        name: str,
        description: str | None = None,
        due_date: datetime | None = None,
        clear_due_date: bool = False,
        status: str | None = None,
    ) -> bool:
        """Update a milestone's properties.

        Args:
            name: Name of the milestone to update
            description: New description (None to keep current)
            due_date: New due date (None to keep current)
            clear_due_date: If True, remove the due date
            status: New status (None to keep current)

        Returns:
            True if milestone was updated, False if not found
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        return self._milestone_ops.update_milestone(
            name=name,
            description=description,
            due_date=due_date,
            clear_due_date=clear_due_date,
            status=status,
        )

    def assign_issue_to_milestone(self, issue_id: str, milestone_name: str) -> bool:
        """Assign an issue to a milestone."""
        # Validate milestone exists
        if not self.get_milestone(milestone_name):
            return False

        return self._issue_ops.assign_issue_to_milestone(issue_id, milestone_name)

    def get_milestone_progress(self, milestone_name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone."""
        return self._milestone_ops.get_milestone_progress(milestone_name)

    # Project management methods
    def list_projects(self) -> list[Project]:
        """List all projects."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self._project_ops.list_projects()

    def get_project(self, project_id: str) -> Project | None:
        """Get a specific project by ID."""
        return self._project_ops.get_project(project_id)

    def save_project(self, project: Project) -> bool:
        """Save an updated project to disk."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        return self._project_ops.save_project(project)

    def update_project(self, project_id: str, **updates) -> Project | None:
        """Update a project with the given fields.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, description, status, priority, etc.)

        Returns:
            Updated Project object if successful, None if not found
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        return self._project_ops.update_project(project_id, **updates)

    def get_backlog_issues(self) -> list[Issue]:
        """Get all issues not assigned to any milestone (backlog)."""
        return self._issue_ops.get_backlog_issues()

    def get_milestone_issues(self, milestone_name: str) -> list[Issue]:
        """Get all issues assigned to a specific milestone."""
        return self._issue_ops.get_milestone_issues(milestone_name)

    def get_issues_by_milestone(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by milestone, including backlog."""
        return self._issue_ops.get_issues_by_milestone()

    def move_issue_to_milestone(
        self, issue_id: str, milestone_name: str | None
    ) -> bool:
        """Move an issue to a milestone or to backlog if milestone_name is None."""
        # Validate milestone exists if provided
        if milestone_name and not self.get_milestone(milestone_name):
            return False

        return self._issue_ops.move_issue_to_milestone(issue_id, milestone_name)

    def get_next_milestone(self) -> Milestone | None:
        """Get the next upcoming milestone based on due date."""
        return self._milestone_ops.get_next_milestone()

    def _get_github_config(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub configuration from config file and credentials.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        return self.github_service.get_github_config()

    def get_team_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        return self.github_service.get_team_members()

    def get_current_user(self) -> str | None:
        """Get the current user from config.

        Returns:
            Current user's name from config if set, None otherwise

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        return self.github_service.get_current_user()

    def get_assigned_issues(self, assignee: str) -> list[Issue]:
        """Get all issues assigned to a specific user."""
        return self.list_issues(assignee=assignee)

    def get_my_issues(self) -> list[Issue]:
        """Get all issues assigned to the current user."""
        current_user = self.get_current_user()
        if not current_user:
            return []
        return self.get_assigned_issues(current_user)

    def get_all_assigned_issues(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by assignee.

        Returns:
            Dictionary mapping assignee usernames to their assigned issues
        """
        all_issues = self.list_issues()
        assigned_issues = {}

        for issue in all_issues:
            if issue.assignee:
                if issue.assignee not in assigned_issues:
                    assigned_issues[issue.assignee] = []
                assigned_issues[issue.assignee].append(issue)

        return assigned_issues

    def _get_cached_team_members(self) -> list[str]:
        """Get team members with caching (5 minute cache).

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        return self.github_service.get_cached_team_members()

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the identity management system.

        This validation integrates with the identity management system while
        maintaining backward compatibility with the original API.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid (backward compatible)
            - (False, error_message) if invalid

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        is_valid, error_msg = self.github_service.validate_assignee(assignee)
        return is_valid, error_msg

    def _legacy_validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Legacy validation fallback for when validation strategy fails.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        return self.github_service._legacy_validate_assignee(assignee)

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        This method should be called after validate_assignee to get the canonical form.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)

        Note: This method delegates to GitHubIntegrationService for actual implementation.
        """
        return self.github_service.get_canonical_assignee(assignee)

    # Git Integration Methods

    def get_git_context(self) -> dict[str, Any]:
        """Get Git repository context information."""
        if not self.git.is_git_repository():
            return {"is_git_repo": False}

        context: dict[str, Any] = {"is_git_repo": True}
        context.update(self.git.get_repository_info())

        # Current branch info
        current_branch = self.git.get_current_branch()
        if current_branch:
            context["current_branch"] = current_branch.name

            # Try to find linked issue
            issue_id = current_branch.extract_issue_id()
            if issue_id:
                issue = self.get_issue(issue_id)
                if issue:
                    context["linked_issue"] = {
                        "id": issue.id,
                        "title": issue.title,
                        "status": issue.status.value,
                        "priority": issue.priority.value,
                    }

        return context

    def get_current_user_from_git(self) -> str | None:
        """Get current user from Git configuration."""
        return self.git.get_current_user()

    def create_issue_with_git_branch(self, title: str, **kwargs) -> Issue | None:
        """Create an issue and optionally create a Git branch for it."""
        # Extract git-specific arguments
        auto_create_branch = kwargs.pop("auto_create_branch", False)
        checkout_branch = kwargs.pop("checkout_branch", True)

        # Create the issue first
        issue = self.create_issue(title, **kwargs)
        if not issue:
            return None

        # If we're in a Git repo and auto_create_branch is requested
        if auto_create_branch and self.git.is_git_repository():
            self.git.create_branch_for_issue(issue, checkout=checkout_branch)

        return issue

    def link_issue_to_current_branch(self, issue_id: str) -> bool:
        """Link an issue to the current Git branch."""
        if not self.git.is_git_repository():
            return False

        current_branch = self.git.get_current_branch()
        if not current_branch:
            return False

        issue = self.get_issue(issue_id)
        if not issue:
            return False

        # Add branch information to issue metadata
        if not hasattr(issue, "git_branches"):
            issue.git_branches = []

        if current_branch.name not in issue.git_branches:
            issue.git_branches.append(current_branch.name)

        # Update the issue
        return self.update_issue(issue_id, git_branches=issue.git_branches) is not None

    def get_commits_for_issue(self, issue_id: str, since: str | None = None) -> list:
        """Get Git commits that reference this issue."""
        if not self.git.is_git_repository():
            return []

        return self.git.get_commits_for_issue(issue_id, since)

    def update_issue_from_git_activity(self, issue_id: str) -> bool:
        """Update issue progress and status based on Git commit activity."""
        if not self.git.is_git_repository():
            return False

        commits = self.get_commits_for_issue(issue_id)
        if not commits:
            return False

        # Get the most recent commit with roadmap updates
        latest_updates = {}
        for commit in commits:
            updates = self.git.parse_commit_message_for_updates(commit)
            if updates:
                latest_updates.update(updates)

        if latest_updates:
            # Update the issue with the extracted information
            self.update_issue(issue_id, **latest_updates)
            return True

        return False

    def suggest_branch_name_for_issue(self, issue_id: str) -> str | None:
        """Suggest a branch name for an issue."""
        issue = self.get_issue(issue_id)
        if not issue or not self.git.is_git_repository():
            return None

        return self.git.suggest_branch_name(issue)

    def get_branch_linked_issues(self) -> dict[str, list[str]]:
        """Get mapping of branches to their linked issue IDs."""
        if not self.git.is_git_repository():
            return {}

        branches = self.git.get_all_branches()
        branch_issues = {}

        for branch in branches:
            issue_id = branch.extract_issue_id()
            if issue_id and self.get_issue(issue_id):
                branch_issues[branch.name] = [issue_id]

        return branch_issues

    def validate_milestone_naming_consistency(self) -> list[dict[str, str]]:
        """Check for inconsistencies between milestone filenames and name fields.

        Returns:
            List of dictionaries with inconsistency details
        """
        inconsistencies = []

        for milestone_file in self.milestones_dir.rglob("*.md"):
            try:
                milestone = MilestoneParser.parse_milestone_file(milestone_file)
                expected_filename = milestone.filename
                actual_filename = milestone_file.name

                if expected_filename != actual_filename:
                    inconsistencies.append(
                        {
                            "file": actual_filename,
                            "name": milestone.name,
                            "expected_filename": expected_filename,
                            "type": "filename_mismatch",
                        }
                    )
            except Exception as e:
                inconsistencies.append(
                    {
                        "file": milestone_file.name,
                        "name": "PARSE_ERROR",
                        "expected_filename": "N/A",
                        "type": "parse_error",
                        "error": str(e),
                    }
                )

        return inconsistencies

    def fix_milestone_naming_consistency(self) -> dict[str, list[str]]:
        """Fix milestone filename inconsistencies by renaming files to match name fields.

        Returns:
            Dictionary with 'renamed' and 'errors' lists
        """
        results = {"renamed": [], "errors": []}
        inconsistencies = self.validate_milestone_naming_consistency()

        for issue in inconsistencies:
            if issue["type"] == "filename_mismatch":
                old_path = self.milestones_dir / issue["file"]
                new_path = self.milestones_dir / issue["expected_filename"]

                try:
                    # Check if target filename already exists
                    if new_path.exists():
                        results["errors"].append(
                            f"Cannot rename {issue['file']} -> {issue['expected_filename']}: target exists"
                        )
                        continue

                    old_path.rename(new_path)
                    results["renamed"].append(
                        f"{issue['file']} -> {issue['expected_filename']}"
                    )
                except Exception as e:
                    results["errors"].append(
                        f"Failed to rename {issue['file']}: {str(e)}"
                    )
            else:
                results["errors"].append(f"Cannot fix {issue['file']}: {issue['type']}")

        return results

    def _generate_id(self) -> str:
        """Generate a unique ID for projects and issues."""
        import uuid

        return str(uuid.uuid4()).replace("-", "")[:8]

    def _normalize_filename(self, title: str) -> str:
        """Normalize a title for use as a filename."""
        import re

        # Replace non-alphanumeric characters with hyphens
        normalized = re.sub(r"[^a-zA-Z0-9\s]", "", title)
        # Replace spaces with hyphens and convert to lowercase
        normalized = re.sub(r"\s+", "-", normalized.strip()).lower()
        # Remove consecutive hyphens
        normalized = re.sub(r"-+", "-", normalized)
        # Remove leading/trailing hyphens
        return normalized.strip("-")
