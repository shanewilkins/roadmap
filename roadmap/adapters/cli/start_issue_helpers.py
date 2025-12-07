"""
DEPRECATED: Use roadmap.core.services.StartIssueService instead.

This module is kept for backward compatibility with tests.
All business logic has been moved to StartIssueService.
"""

from roadmap.core.services import StartIssueService

__all__ = ["StartDateParser", "StartIssueWorkflow", "StartIssueDisplay"]


class StartDateParser:
    """DEPRECATED: Use StartIssueService.parse_start_date instead."""

    @staticmethod
    def parse_start_date(date_str=None):
        """DEPRECATED: Use StartIssueService.parse_start_date instead."""
        try:
            return StartIssueService.parse_start_date(date_str)
        except ValueError:
            return None


class StartIssueWorkflow:
    """DEPRECATED: Use StartIssueService instead."""

    @staticmethod
    def start_work(core, issue_id, start_date):
        """DEPRECATED: Use StartIssueService.start_work instead."""
        service = StartIssueService(core)
        return service.start_work(issue_id, start_date)

    @staticmethod
    def should_create_branch(git_branch_flag, core):
        """DEPRECATED: Use StartIssueService.should_create_branch instead."""
        service = StartIssueService(core)
        return service.should_create_branch(git_branch_flag)


class StartIssueDisplay:
    """DEPRECATED: Use StartIssueService display methods instead."""

    @staticmethod
    def show_started(issue, start_date, console):
        """DEPRECATED: Use StartIssueService.display_started instead."""
        console.print(f"🚀 Started work on: {issue.title}", style="bold green")
        console.print(
            f"   Started: {start_date.strftime('%Y-%m-%d %H:%M')}", style="cyan"
        )
        console.print("   Status: In Progress", style="yellow")

    @staticmethod
    def show_branch_created(branch_name, checkout, console):
        """DEPRECATED: Use StartIssueService.display_branch_created instead."""
        console.print(f"🌿 Created Git branch: {branch_name}", style="green")
        if checkout:
            console.print(f"✅ Checked out branch: {branch_name}", style="green")

    @staticmethod
    def show_branch_warning(core, console):
        """DEPRECATED: Use StartIssueService.display_branch_warning instead."""
        try:
            status_output = core.git._run_git_command(["status", "--porcelain"]) or ""
            if status_output.strip():
                console.print(
                    "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                    style="yellow",
                )
            else:
                console.print(
                    "⚠️  Failed to create or checkout branch. See git for details.",
                    style="yellow",
                )
        except Exception:
            console.print(
                "⚠️  Failed to create or checkout branch. See git for details.",
                style="yellow",
            )
