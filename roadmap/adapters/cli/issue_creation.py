"""
DEPRECATED: Use roadmap.core.services.IssueCreationService instead.

This module is kept for backward compatibility with tests.
All business logic has been moved to IssueCreationService.
"""

from roadmap.core.services import IssueCreationService

__all__ = ["AssigneeResolver", "GitBranchCreator", "IssueDisplayFormatter"]


class AssigneeResolver:
    """DEPRECATED: Use IssueCreationService.resolve_and_validate_assignee instead."""

    def __init__(self, core):
        self.service = IssueCreationService(core)

    def resolve_assignee(self, assignee=None, auto_detect=True):
        """DEPRECATED: Use IssueCreationService.resolve_and_validate_assignee instead."""
        return self.service.resolve_and_validate_assignee(assignee, auto_detect)


class GitBranchCreator:
    """DEPRECATED: Use IssueCreationService.create_branch_for_issue instead."""

    def __init__(self, core):
        self.service = IssueCreationService(core)

    def create_branch(self, issue, branch_name=None, checkout=True, force=False):
        """DEPRECATED: Use IssueCreationService.create_branch_for_issue instead."""
        return self.service.create_branch_for_issue(issue, branch_name, checkout, force)


class IssueDisplayFormatter:
    """DEPRECATED: Use IssueCreationService.format_created_issue_display instead."""

    @staticmethod
    def display_created_issue(issue, milestone=None, assignee=None):
        """DEPRECATED: Use IssueCreationService.format_created_issue_display instead."""
        from roadmap.common.console import get_console

        console = get_console()
        console.print(f"✅ Created issue: {issue.title}", style="bold green")
        console.print(f"   ID: {issue.id}", style="cyan")
        console.print(f"   Type: {issue.issue_type.value.title()}", style="blue")
        console.print(f"   Priority: {issue.priority.value}", style="yellow")
        if milestone:
            console.print(f"   Milestone: {milestone}", style="blue")
        if issue.assignee:
            console.print(f"   Assignee: {issue.assignee}", style="magenta")
        if issue.estimated_hours:
            console.print(
                f"   Estimated: {issue.estimated_time_display}", style="green"
            )
        if hasattr(issue, "depends_on") and issue.depends_on:
            console.print(
                f"   Depends on: {', '.join(issue.depends_on)}", style="orange1"
            )
        if hasattr(issue, "blocks") and issue.blocks:
            console.print(f"   Blocks: {', '.join(issue.blocks)}", style="red1")
        console.print(f"   File: .roadmap/issues/{issue.filename}", style="dim")
