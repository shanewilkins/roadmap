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
Old code should update imports from "from roadmap.application.core import RoadmapCore"
to "from roadmap.application.core import RoadmapCore".

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

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .services import (
    ConfigurationService,
    IssueService,
    MilestoneService,
    ProjectService,
    VisualizationService,
)
from ..infrastructure.storage import StateManager
from ..shared.errors import ValidationError, RoadmapError
from ..infrastructure.git import GitIntegration
from ..domain import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Project,
    Status,
)
from ..parser import IssueParser, MilestoneParser
from ..security import (
    create_secure_directory,
    create_secure_file,
)


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

        # Initialize Git integration
        self.git = GitIntegration(self.root_path)

        # Initialize database manager
        self.db = StateManager(self.roadmap_dir / "state.db")

        # Initialize service layer
        self.issue_service = IssueService(self.db, self.issues_dir)
        self.milestone_service = MilestoneService(
            self.db, self.milestones_dir, self.issues_dir
        )
        self.project_service = ProjectService(
            self.db, self.projects_dir, self.milestones_dir
        )
        self.visualization_service = VisualizationService(self.db, self.artifacts_dir)
        self.config_service = ConfigurationService()

        # Cache for team members to avoid repeated API calls
        self._team_members_cache = None
        self._cache_timestamp = None

        # Cache for canonical assignee resolution
        self._last_canonical_assignee = None

    def is_initialized(self) -> bool:
        """Check if roadmap is initialized in current directory."""
        return self.roadmap_dir.exists() and self.config_file.exists()

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
            from ..infrastructure.git import GitHookManager

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

    @classmethod
    def find_existing_roadmap(
        cls, root_path: Path | None = None
    ) -> Optional["RoadmapCore"]:
        """Find an existing roadmap directory in the current path.

        Searches for common roadmap directory names and returns a RoadmapCore
        instance if found, or None if no roadmap is detected.
        """
        search_path = root_path or Path.cwd()

        # Common roadmap directory names to search for
        possible_names = [".roadmap"]

        # Also check for any directory containing the expected structure
        for item in search_path.iterdir():
            if item.is_dir():
                possible_names.append(item.name)

        # Check each possible directory
        for dir_name in possible_names:
            try:
                potential_core = cls(root_path=search_path, roadmap_dir_name=dir_name)
                if potential_core.is_initialized():
                    return potential_core
            except (OSError, PermissionError, sqlite3.OperationalError):
                # Skip directories that can't be accessed or have permission issues
                continue

        return None

    def initialize(self) -> None:
        """Initialize a new roadmap in the current directory."""
        if self.is_initialized():
            raise ValueError("Roadmap already initialized in this directory")

        # Create directory structure with secure permissions
        create_secure_directory(
            self.roadmap_dir, 0o755
        )  # Owner full, group/other read/execute
        create_secure_directory(self.issues_dir, 0o755)
        create_secure_directory(self.milestones_dir, 0o755)
        create_secure_directory(self.projects_dir, 0o755)
        create_secure_directory(self.templates_dir, 0o755)
        create_secure_directory(self.artifacts_dir, 0o755)

        # Update .gitignore to exclude roadmap local data
        self._update_gitignore()

        # Copy templates
        self._create_default_templates()

        # Create default config file (config.yaml)

    def _create_default_templates(self) -> None:
        """Create default templates."""
        # Issue template
        issue_template = """---
id: "{{ issue_id }}"
title: "{{ title }}"
priority: "medium"
status: "todo"
milestone: ""
labels: []
github_issue: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
assignee: ""
---

# {{ title }}

## Description

Brief description of the issue or feature request.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes

Any technical details, considerations, or implementation notes.

## Related Issues

- Links to related issues
- Dependencies

## Additional Context

Any additional context, screenshots, or examples."""

        with create_secure_file(self.templates_dir / "issue.md", "w", 0o644) as f:
            f.write(issue_template)

        # Milestone template
        milestone_template = """---
name: "{{ milestone_name }}"
description: "{{ description }}"
due_date: "{{ due_date }}"
status: "open"
github_milestone: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
---

# {{ milestone_name }}

## Description

{{ description }}

## Goals

- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## Success Criteria

Define what success looks like for this milestone.

## Notes

Any additional notes or considerations for this milestone."""

        with create_secure_file(self.templates_dir / "milestone.md", "w", 0o644) as f:
            f.write(milestone_template)

        # Project template
        project_template = """---
id: "{{ project_id }}"
name: "{{ project_name }}"
description: "{{ project_description }}"
status: "planning"
priority: "medium"
owner: "{{ project_owner }}"
start_date: "{{ start_date }}"
target_end_date: "{{ target_end_date }}"
actual_end_date: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
milestones:
  - "{{ milestone_1 }}"
  - "{{ milestone_2 }}"
estimated_hours: {{ estimated_hours }}
actual_hours: null
---

# {{ project_name }}

## Project Overview

{{ project_description }}

**Project Owner:** {{ project_owner }}
**Status:** {{ status }}
**Timeline:** {{ start_date }} → {{ target_end_date }}

## Objectives

- [ ] Objective 1
- [ ] Objective 2
- [ ] Objective 3

## Milestones & Timeline

{% for milestone in milestones %}
- **{{ milestone }}** - [Link to milestone](../milestones/{{ milestone }}.md)
{% endfor %}

## Timeline Tracking

- **Start Date:** {{ start_date }}
- **Target End Date:** {{ target_end_date }}
- **Actual End Date:** {{ actual_end_date }}
- **Estimated Hours:** {{ estimated_hours }}
- **Actual Hours:** {{ actual_hours }}

## Notes

Project notes and additional context.

---
*Last updated: {{ updated_date }}*"""

        with create_secure_file(self.templates_dir / "project.md", "w", 0o644) as f:
            f.write(project_template)

    def _update_gitignore(self) -> None:
        """Update .gitignore to exclude roadmap local data from version control."""
        gitignore_path = self.root_path / ".gitignore"

        # Define patterns to ignore relative to project root
        roadmap_patterns = [
            f"{self.roadmap_dir_name}/artifacts/",
            f"{self.roadmap_dir_name}/backups/",
            f"{self.roadmap_dir_name}/*.tmp",
            f"{self.roadmap_dir_name}/*.lock",
        ]
        gitignore_comment = (
            "# Roadmap local data (generated exports, backups, temp files)"
        )

        # Read existing .gitignore if it exists
        existing_lines = []
        if gitignore_path.exists():
            existing_lines = gitignore_path.read_text().splitlines()

        # Check which patterns are already present
        missing_patterns = []
        for pattern in roadmap_patterns:
            if not any(line.strip() == pattern for line in existing_lines):
                missing_patterns.append(pattern)

        if missing_patterns:
            # Add missing patterns to .gitignore
            if existing_lines and not existing_lines[-1].strip() == "":
                existing_lines.append("")  # Add blank line if needed

            existing_lines.append(gitignore_comment)
            existing_lines.extend(missing_patterns)

            # Write updated .gitignore
            gitignore_path.write_text("\n".join(existing_lines) + "\n")

    def load_config(self) -> dict:
        """Load roadmap configuration.
        
        Note: RoadmapConfig class moved to application layer.
        This method returns a dict representation.
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")
        
        # Load from config.yaml file
        import yaml
        with open(self.config_file, "r") as f:
            return yaml.safe_load(f) or {}

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

        return self.issue_service.create_issue(
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

        return self.issue_service.list_issues(
            milestone=milestone,
            status=status,
            priority=priority,
            issue_type=issue_type,
            assignee=assignee,
        )

    def get_issue(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID."""
        return self.issue_service.get_issue(issue_id)

    def update_issue(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue."""
        return self.issue_service.update_issue(issue_id, **updates)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue."""
        return self.issue_service.delete_issue(issue_id)

    def create_milestone(
        self, name: str, description: str = "", due_date: datetime | None = None
    ) -> Milestone:
        """Create a new milestone."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self.milestone_service.create_milestone(
            name=name, description=description, due_date=due_date
        )

    def list_milestones(self) -> list[Milestone]:
        """List all milestones."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self.milestone_service.list_milestones()

    def get_milestone(self, name: str) -> Milestone | None:
        """Get a specific milestone by name (searches by YAML name field, not filename)."""
        return self.milestone_service.get_milestone(name)

    def delete_milestone(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Name of the milestone to delete

        Returns:
            True if milestone was deleted, False if not found
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        return self.milestone_service.delete_milestone(name)

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

        return (
            self.milestone_service.update_milestone(
                name=name,
                description=description,
                due_date=due_date,
                clear_due_date=clear_due_date,
                status=status,
            )
            is not None
        )

    def assign_issue_to_milestone(self, issue_id: str, milestone_name: str) -> bool:
        """Assign an issue to a milestone."""
        issue = self.get_issue(issue_id)
        if not issue:
            return False

        milestone = self.get_milestone(milestone_name)
        if not milestone:
            return False

        issue.milestone = milestone_name
        from .timezone_utils import now_utc

        issue.updated = now_utc()

        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return True

    def get_milestone_progress(self, milestone_name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone."""
        return self.milestone_service.get_milestone_progress(milestone_name)

    # Project management methods
    def list_projects(self) -> list[Project]:
        """List all projects."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return self.project_service.list_projects()

    def get_project(self, project_id: str) -> Project | None:
        """Get a specific project by ID."""
        return self.project_service.get_project(project_id)

    def save_project(self, project: Project) -> bool:
        """Save an updated project to disk."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        return self.project_service.save_project(project)

    def get_backlog_issues(self) -> list[Issue]:
        """Get all issues not assigned to any milestone (backlog)."""
        all_issues = self.list_issues()
        return [issue for issue in all_issues if issue.is_backlog]

    def get_milestone_issues(self, milestone_name: str) -> list[Issue]:
        """Get all issues assigned to a specific milestone."""
        all_issues = self.list_issues()
        return [issue for issue in all_issues if issue.milestone == milestone_name]

    def get_issues_by_milestone(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by milestone, including backlog."""
        all_issues = self.list_issues()
        grouped = {"Backlog": []}

        # Add backlog issues
        for issue in all_issues:
            if issue.is_backlog:
                grouped["Backlog"].append(issue)
            else:
                milestone_name = issue.milestone
                if milestone_name is None:
                    # Issues without milestone go to Backlog
                    grouped["Backlog"].append(issue)
                else:
                    if milestone_name not in grouped:
                        grouped[milestone_name] = []
                    grouped[milestone_name].append(issue)

        return grouped

    def move_issue_to_milestone(
        self, issue_id: str, milestone_name: str | None
    ) -> bool:
        """Move an issue to a milestone or to backlog if milestone_name is None."""
        issue = self.get_issue(issue_id)
        if not issue:
            return False

        # Validate milestone exists if provided
        if milestone_name and not self.get_milestone(milestone_name):
            return False

        # Update issue milestone
        issue.milestone = milestone_name
        from .timezone_utils import now_utc

        issue.updated = now_utc()

        # Save updated issue
        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return True

    def get_next_milestone(self) -> Milestone | None:
        """Get the next upcoming milestone based on due date."""
        milestones = self.list_milestones()

        # Filter for open milestones with due dates
        upcoming_milestones = [
            m
            for m in milestones
            if m.status == MilestoneStatus.OPEN and m.due_date is not None
        ]

        if not upcoming_milestones:
            return None

        # Sort by due date and return the earliest
        # Handle timezone-aware vs timezone-naive datetime comparison
        def get_sortable_date(milestone):
            due_date = milestone.due_date
            # due_date should not be None since we filtered above, but be safe
            if due_date is None:
                from datetime import datetime

                return datetime.max  # Put None dates at the end
            # Convert timezone-aware dates to naive for comparison
            if due_date.tzinfo is not None:
                return due_date.replace(tzinfo=None)
            return due_date

        upcoming_milestones.sort(key=get_sortable_date)
        return upcoming_milestones[0]

    def _get_github_config(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub configuration from config file and credentials.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        try:
            from .credentials import get_credential_manager

            config = self.load_config()
            github_config = config.github or {}

            # Get owner and repo from config
            owner = github_config.get("owner")
            repo = github_config.get("repo")

            if not owner or not repo:
                return None, None, None

            # Get token from credentials manager or environment
            credential_manager = get_credential_manager()
            token = credential_manager.get_token()

            if not token:
                import os

                token = os.getenv("GITHUB_TOKEN")

            return token, owner, repo

        except Exception:
            return None, None, None

    def get_team_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        try:
            from .github_client import GitHubClient

            token, owner, repo = self._get_github_config()
            if not token or not owner or not repo:
                return []

            # Get team members
            client = GitHubClient(token=token, owner=owner, repo=repo)
            return client.get_team_members()
        except Exception:
            # Return empty list if GitHub is not configured or accessible
            return []

    def get_current_user(self) -> str | None:
        """Get the current GitHub user.

        Returns:
            Current user's GitHub username if configured, None otherwise
        """
        try:
            from .github_client import GitHubClient

            token, owner, repo = self._get_github_config()
            if not token or not owner or not repo:
                return None

            # Get current user
            client = GitHubClient(token=token, owner=owner, repo=repo)
            return client.get_current_user()
        except Exception:
            # Return None if GitHub is not configured or accessible
            return None

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
        """Get team members with caching (5 minute cache)."""
        from datetime import datetime, timedelta

        # Check if cache is valid (5 minutes)
        if (
            self._team_members_cache is not None
            and self._cache_timestamp is not None
            and datetime.now() - self._cache_timestamp < timedelta(minutes=5)
        ):
            return self._team_members_cache

        # Refresh cache
        team_members = self.get_team_members()
        self._team_members_cache = team_members
        self._cache_timestamp = datetime.now()

        return team_members

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
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty"

        assignee = assignee.strip()

        try:
            # Try identity management system first
            from .identity import IdentityManager

            identity_manager = IdentityManager(self.root_path)
            is_valid, result, profile = identity_manager.resolve_assignee(assignee)

            if is_valid:
                # Store canonical form for later retrieval but return empty string for compatibility
                self._last_canonical_assignee = (
                    profile.canonical_id if profile else result
                )
                return True, ""
            else:
                # If identity system failed, check if we should fall back to GitHub validation
                token, owner, repo = self._get_github_config()

                # If GitHub is configured and identity system suggests GitHub fallback
                if (
                    token
                    and owner
                    and repo
                    and identity_manager.config.validation_mode
                    in ["hybrid", "github-only"]
                ):
                    # Fall back to GitHub validation for hybrid/github-only mode
                    team_members = self._get_cached_team_members()
                    if team_members and assignee in team_members:
                        self._last_canonical_assignee = assignee
                        return True, ""

                    # Do full validation via API
                    from .github_client import GitHubClient

                    client = GitHubClient(token=token, owner=owner, repo=repo)
                    github_valid, github_error = client.validate_assignee(assignee)
                    if github_valid:
                        self._last_canonical_assignee = assignee
                        return True, ""
                    else:
                        return False, github_error

                # If no GitHub config and identity system is in local/hybrid mode,
                # accept reasonable names (for local-only usage)
                elif not (
                    token and owner and repo
                ) and identity_manager.config.validation_mode in [
                    "local-only",
                    "hybrid",
                ]:
                    # Basic validation for local usage
                    if len(assignee) >= 2 and not any(
                        char in assignee for char in "<>{}[]()"
                    ):
                        self._last_canonical_assignee = assignee
                        return True, ""
                    else:
                        return False, f"'{assignee}' is not a valid assignee name"

                # No fallback available, return identity system result
                return False, result

        except Exception:
            # If identity management fails, fall back to legacy validation
            try:
                token, owner, repo = self._get_github_config()
                if not token or not owner or not repo:
                    # If GitHub is not configured, allow any assignee without validation
                    # This supports local-only roadmap usage without GitHub integration
                    self._last_canonical_assignee = assignee
                    return True, ""

                # GitHub is configured - perform validation against repository access

                # First check against cached team members for performance
                team_members = self._get_cached_team_members()
                if team_members and assignee in team_members:
                    self._last_canonical_assignee = assignee
                    return True, ""

                # If not in cache or cache is empty, do full validation via API
                from .github_client import GitHubClient

                client = GitHubClient(token=token, owner=owner, repo=repo)

                # This will do the full GitHub API validation
                github_valid, github_error = client.validate_assignee(assignee)
                if github_valid:
                    self._last_canonical_assignee = assignee
                    return True, ""
                else:
                    return False, github_error

            except Exception as fallback_error:
                # If validation fails due to network/API issues, allow the assignment
                # but log a warning that validation couldn't be performed
                error_handler = ErrorHandler()
                error_handler.handle_error(
                    ValidationError(
                        f"Could not validate assignee '{assignee}' - validation unavailable",
                        field="assignee",
                        value=assignee,
                        severity=ErrorSeverity.WARNING,
                        cause=fallback_error,
                    ),
                    show_traceback=False,
                    exit_on_critical=False,
                )
                warning_msg = f"Warning: Could not validate assignee (validation unavailable): {str(fallback_error)}"
                self._last_canonical_assignee = assignee
                return True, warning_msg

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        This method should be called after validate_assignee to get the canonical form.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        # Try to get from identity management system
        try:
            from .identity import IdentityManager

            identity_manager = IdentityManager(self.root_path)
            is_valid, result, profile = identity_manager.resolve_assignee(assignee)

            if is_valid and profile:
                return profile.canonical_id
            elif is_valid:
                return result
        except Exception:
            pass

        # Fallback to original assignee
        return assignee

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

        for milestone_file in self.milestones_dir.glob("*.md"):
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
