"""
Presentation layer for project status display logic.

Handles all user-facing output:
- Displaying milestone progress
- Rendering issue status tables
- Showing roadmap summaries
- Formatting status information
"""

from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from roadmap.common.console import get_console
from roadmap.core.domain import Status

console = get_console()


class MilestoneProgressPresenter:
    """Presenter for milestone progress display."""

    @staticmethod
    def show_milestone_header() -> None:
        """Display milestone section header."""
        console.print("\n🎯 Milestones:", style="bold cyan")

    @staticmethod
    def show_milestone_progress(milestone_name: str, progress: dict) -> None:
        """Display progress for a single milestone.

        Args:
            milestone_name: Name of the milestone
            progress: Progress dictionary with 'total', 'completed', 'percentage'
        """
        console.print(f"\n  {milestone_name}")

        if progress.get("total", 0) > 0:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
                transient=True,
            ) as progress_bar:
                completed = progress.get("completed", 0)
                total = progress.get("total", 0)
                progress_bar.add_task(
                    f"    Progress ({completed}/{total})",
                    total=total,
                    completed=completed,
                )
        else:
            console.print("    No issues assigned", style="dim")

    @staticmethod
    def show_all_milestones(milestones: list, milestone_progress: dict) -> None:
        """Display all milestones with progress.

        Args:
            milestones: List of milestone objects
            milestone_progress: Dictionary mapping milestone name to progress
        """
        MilestoneProgressPresenter.show_milestone_header()
        for milestone in milestones:
            progress = milestone_progress.get(milestone.name, {})
            MilestoneProgressPresenter.show_milestone_progress(milestone.name, progress)


class IssueStatusPresenter:
    """Presenter for issue status display."""

    @staticmethod
    def get_status_style(status: Status) -> str:
        """Get display style for a status.

        Args:
            status: Status enum value

        Returns:
            Rich style string
        """
        styles = {
            Status.TODO: "white",
            Status.IN_PROGRESS: "yellow",
            Status.BLOCKED: "red",
            Status.REVIEW: "blue",
            Status.CLOSED: "green",
        }
        return styles.get(status, "white")

    @staticmethod
    def show_issue_status_header() -> None:
        """Display issue status section header."""
        console.print("\n📋 Issues by Status:", style="bold cyan")

    @staticmethod
    def show_issue_status_table(issue_counts: dict) -> None:
        """Display table of issue counts by status.

        Args:
            issue_counts: Dictionary mapping Status enum to count
        """
        if not issue_counts or not any(issue_counts.values()):
            console.print("  No issues found", style="dim")
            return

        status_table = Table(show_header=False, box=None)
        status_table.add_column("Status", style="white", width=15)
        status_table.add_column("Count", style="cyan", width=10)

        for status in Status:
            count = issue_counts.get(status, 0)
            if count > 0:  # Only show statuses that have issues
                style = IssueStatusPresenter.get_status_style(status)
                status_table.add_row(
                    Text(f"  {status.value}", style=style),
                    str(count),
                )

        console.print(status_table)

    @staticmethod
    def show_all_issue_statuses(issue_counts: dict) -> None:
        """Display all issue statuses with counts.

        Args:
            issue_counts: Dictionary mapping Status enum to count
        """
        IssueStatusPresenter.show_issue_status_header()
        IssueStatusPresenter.show_issue_status_table(issue_counts)


class RoadmapStatusPresenter:
    """Presenter for overall roadmap status."""

    @staticmethod
    def show_empty_state() -> None:
        """Display message when no issues or milestones exist."""
        console.print("\n📝 No issues or milestones found.", style="yellow")
        console.print("Get started with:")
        console.print("  roadmap issue create 'My first issue'")
        console.print("  roadmap milestone create 'My first milestone'")

    @staticmethod
    def show_status_header() -> None:
        """Display main status header."""
        console.print("📊 Roadmap Status", style="bold blue")

    @staticmethod
    def show_roadmap_summary(summary: dict) -> None:
        """Display comprehensive roadmap summary.

        Args:
            summary: Dictionary with roadmap summary data
        """
        console.print("\n📈 Summary:", style="bold cyan")
        console.print(
            f"  Total Issues: {summary.get('total_issues', 0)}", style="white"
        )
        console.print(
            f"  Active Issues: {summary.get('active_issues', 0)}", style="yellow"
        )
        blocked = summary.get("blocked_issues", 0)
        if blocked > 0:
            console.print(f"  Blocked Issues: {blocked}", style="red")
        console.print(
            f"  Total Milestones: {summary.get('total_milestones', 0)}", style="white"
        )
        completed = summary.get("completed_milestones", 0)
        total = summary.get("total_milestones", 0)
        if total > 0:
            console.print(f"  Completed Milestones: {completed}/{total}", style="green")

    @staticmethod
    def show_error(error_message: str) -> None:
        """Display error message.

        Args:
            error_message: Error message to display
        """
        console.print(f"❌ Failed to show status: {error_message}", style="bold red")
