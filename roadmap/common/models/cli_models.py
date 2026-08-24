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
    interactive: bool = True
    yes: bool = False
    dry_run: bool = False
    force: bool = False
    template: str | None = None
    template_path: str | None = None


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
