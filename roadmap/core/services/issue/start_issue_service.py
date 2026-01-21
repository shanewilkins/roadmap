"""Service for starting work on issues.

Consolidates business logic for updating issue status, setting start dates,
and optionally creating Git branches.
"""

from datetime import UTC, datetime

from roadmap.common.console import get_console
from roadmap.core.domain import Status


class StartIssueService:
    """Service for starting work on issues."""

    def __init__(self, core):
        """Initialize service with core instance.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
        self._console = get_console()

    # ─────────────────────────────────────────────────────────────────────────
    # Start Date Parsing
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_start_date(date_str: str | None) -> datetime:
        """Parse start date from string input.

        Args:
            date_str: Date string in format YYYY-MM-DD or YYYY-MM-DD HH:MM

        Returns:
            Parsed datetime, or current time if not provided or invalid

        Raises:
            ValueError: If date string is invalid
        """
        if not date_str:
            return datetime.now(UTC)

        # Try full datetime format first
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # Try date-only format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"
            ) from e

    # ─────────────────────────────────────────────────────────────────────────
    # Start Work Workflow
    # ─────────────────────────────────────────────────────────────────────────

    def start_work(self, issue_id: str, start_date: datetime) -> object | None:
        """Update issue to start work.

        Sets status to IN_PROGRESS, sets actual start date, and initializes
        progress tracking.

        Args:
            issue_id: ID of issue to start
            start_date: Datetime to set as start time

        Returns:
            Updated issue if successful, None otherwise
        """
        return self.core.issues.update(
            issue_id,
            actual_start_date=start_date,
            status=Status.IN_PROGRESS,
            progress_percentage=0.0,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Branch Creation Decision
    # ─────────────────────────────────────────────────────────────────────────

    def should_create_branch(self, git_branch_flag: bool) -> bool:
        """Determine if git branch should be created based on flag and config.

        Currently only respects explicit --create-branch flag.
        Auto-creation can be re-enabled via config in the future.

        Args:
            git_branch_flag: Whether --create-branch flag was passed

        Returns:
            Whether to create a branch
        """
        if git_branch_flag:
            return True

        # Check config for auto_branch default (disabled for now - can be re-enabled later)
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Display Results
    # ─────────────────────────────────────────────────────────────────────────

    def display_started(self, issue, start_date: datetime) -> None:
        """Display success message for started issue.

        Args:
            issue: Issue that was started
            start_date: Datetime when work started
        """
        self._console.print(f"🚀 Started work on: {issue.title}", style="bold green")
        self._console.print(
            f"   Started: {start_date.strftime('%Y-%m-%d %H:%M')}", style="cyan"
        )
        self._console.print("   Status: In Progress", style="yellow")

    def display_branch_created(self, branch_name: str, checkout: bool) -> None:
        """Display git branch creation success.

        Args:
            branch_name: Name of created branch
            checkout: Whether branch was checked out
        """
        self._console.print(
            f"🌿 Created Git branch: {branch_name}",
            style="green",
        )
        if checkout:
            self._console.print(
                f"✅ Checked out branch: {branch_name}",
                style="green",
            )

    def display_branch_warning(self) -> None:
        """Display warning when branch creation fails."""
        try:
            status_output = (
                self.core.git._run_git_command(["status", "--porcelain"]) or ""
            )
            if status_output.strip():
                self._console.print(
                    "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                    style="yellow",
                )
            else:
                self._console.print(
                    "⚠️  Failed to create or checkout branch. See git for details.",
                    style="yellow",
                )
        except Exception:
            self._console.print(
                "⚠️  Failed to create or checkout branch. See git for details.",
                style="yellow",
            )
