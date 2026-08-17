"""Dataclasses for clean CLI parameter passing.

These models provide structured, documented parameter groups for complex CLI commands.
Benefits:
- Reduces cognitive load on function signatures
- Self-documenting API with field descriptions
- Easy to extend without breaking changes
- Type-safe parameter handling
"""

from dataclasses import dataclass


@dataclass
class IssueListParams:
    """Parameters for listing issues."""

    filter_type: str | None = None
    milestone: str | None = None
    backlog: bool = False
    unassigned: bool = False
    open: bool = False
    blocked: bool = False
    next_milestone: bool = False
    assignee: str | None = None
    my_issues: bool = False
    status: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    overdue: bool = False


@dataclass
class InitParams:
    """Parameters for initialization command."""

    name: str
    project_name: str | None = None
    description: str | None = None
    skip_project: bool = False
    skip_github: bool = False
    sync_backend: str = "github"
    github_repo: str | None = None
    github_token: str | None = None
    interactive: bool = True
    yes: bool = False
    dry_run: bool = False
    force: bool = False
    template: str | None = None
    template_path: str | None = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        from roadmap.common.constants import SyncBackend

        # Validate sync_backend matches enum values
        valid_backends = {backend.value for backend in SyncBackend}
        if self.sync_backend not in valid_backends:
            raise ValueError(
                f"Invalid sync_backend '{self.sync_backend}'. "
                f"Must be one of: {', '.join(sorted(valid_backends))}"
            )


@dataclass
class CleanupParams:
    """Parameters for cleanup command."""

    keep: int = 10
    days: int | None = None
    dry_run: bool = False
    force: bool = False
    backups_only: bool = False
    check_folders: bool = False
    check_duplicates: bool = False
    check_malformed: bool = False
    verbose: bool = False
