"""Dataclasses for clean CLI parameter passing.

These models provide structured, documented parameter groups for complex CLI commands.
Benefits:
- Reduces cognitive load on function signatures
- Self-documenting API with field descriptions
- Easy to extend without breaking changes
- Type-safe parameter handling
"""

from dataclasses import dataclass, field


@dataclass
class IssueCreateParams:
    """Parameters for creating an issue."""

    title: str
    priority: str | None = None
    issue_type: str | None = None
    milestone: str | None = None
    assignee: str | None = None
    labels: tuple = field(default_factory=tuple)
    estimate: float | None = None
    depends_on: tuple = field(default_factory=tuple)
    blocks: tuple = field(default_factory=tuple)
    description: str | None = None


@dataclass
class IssueUpdateParams:
    """Parameters for updating an issue."""

    issue_id: str
    title: str | None = None
    priority: str | None = None
    status: str | None = None
    assignee: str | None = None
    milestone: str | None = None
    description: str | None = None
    estimate: float | None = None
    reason: str | None = None


@dataclass
class IssueGitParams:
    """Git-related parameters for issues."""

    git_branch: bool = False
    checkout: bool = False
    branch_name: str | None = None
    force: bool = False


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
