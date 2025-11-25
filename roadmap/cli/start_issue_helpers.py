"""
Helpers for start issue command.
"""

from datetime import datetime

from roadmap.domain import Status


class StartDateParser:
    """Parse start date from string input."""

    @staticmethod
    def parse_start_date(date_str: str | None) -> datetime | None:
        """
        Parse start date from string.

        Args:
            date_str: Date string in format YYYY-MM-DD or YYYY-MM-DD HH:MM

        Returns:
            Parsed datetime or None if invalid
        """
        if not date_str:
            return datetime.now()

        # Try full datetime format first
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # Try date-only format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None


class StartIssueWorkflow:
    """Orchestrate starting work on an issue."""

    @staticmethod
    def start_work(core, issue_id: str, start_date: datetime):
        """
        Update issue to start work.

        Returns:
            Updated issue if successful, None otherwise
        """
        return core.update_issue(
            issue_id,
            actual_start_date=start_date,
            status=Status.IN_PROGRESS,
            progress_percentage=0.0,
        )

    @staticmethod
    def should_create_branch(git_branch_flag: bool, core) -> bool:
        """Determine if git branch should be created based on flag and config."""
        if git_branch_flag:
            return True

        # Check config for auto_branch default (disabled for now - can be re-enabled later)
        return False


class StartIssueDisplay:
    """Display results of starting an issue."""

    @staticmethod
    def show_started(issue, start_date: datetime, console):
        """Display success message for started issue."""
        console.print(f"🚀 Started work on: {issue.title}", style="bold green")
        console.print(
            f"   Started: {start_date.strftime('%Y-%m-%d %H:%M')}", style="cyan"
        )
        console.print("   Status: In Progress", style="yellow")

    @staticmethod
    def show_branch_created(branch_name: str, checkout: bool, console):
        """Display git branch creation success."""
        console.print(
            f"🌿 Created Git branch: {branch_name}",
            style="green",
        )
        if checkout:
            console.print(
                f"✅ Checked out branch: {branch_name}",
                style="green",
            )

    @staticmethod
    def show_branch_warning(core, console):
        """Display warning when branch creation fails."""
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
