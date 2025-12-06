"""
Presentation layer for milestone list command.

Handles all display logic related to:
- Rendering milestone tables
- Formatting milestone data
- Styling milestone information
- Empty state handling
"""

from rich.table import Table

from roadmap.common.console import get_console
from roadmap.common.logging import get_logger

console = get_console()
logger = get_logger(__name__)


class MilestoneTablePresenter:
    """Presenter for rendering milestone data in table format."""

    @staticmethod
    def display_milestone_table(
        milestones: list,
        progress: dict,
        estimates: dict,
        get_due_date_status_fn,
    ) -> None:
        """Display milestones in a formatted Rich table.

        Args:
            milestones: List of milestone objects
            progress: Dictionary mapping milestone names to progress dicts
            estimates: Dictionary mapping milestone names to estimate strings
            get_due_date_status_fn: Function to get due date string and styling
        """
        try:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Due Date", style="yellow", width=12)
            table.add_column("Status", style="green", width=10)
            table.add_column("Progress", style="blue", width=12)
            table.add_column("Estimate", style="green", width=10)

            for ms in milestones:
                # Get progress
                ms_progress = progress.get(ms.name, {})
                progress_text = (
                    f"{ms_progress.get('completed', 0)}/{ms_progress.get('total', 0)}"
                )

                # Get estimate
                estimate_text = estimates.get(ms.name, "-")

                # Format due date with styling
                due_date_text, style = get_due_date_status_fn(ms)
                if style:
                    due_date_text = f"[{style}]{due_date_text}[/{style}]"

                # Add row to table
                table.add_row(
                    ms.name,
                    ms.description or "-",
                    due_date_text,
                    ms.status.value,
                    progress_text,
                    estimate_text,
                )

            console.print(table)
        except Exception as e:
            logger.error(
                "failed_to_display_milestone_table",
                error=str(e),
            )
            console.print("❌ Failed to display milestone table", style="bold red")


class MilestoneListPresenter:
    """Presenter for milestone list display."""

    @staticmethod
    def show_empty_state() -> None:
        """Display empty state when no milestones found."""
        console.print("📋 No milestones found.", style="yellow")
        console.print(
            "Create one with: roadmap milestone create 'Milestone name'",
            style="dim",
        )

    @staticmethod
    def show_no_upcoming_milestones() -> None:
        """Display message when no upcoming milestones with due dates found."""
        console.print("📋 No upcoming milestones with due dates found.", style="yellow")
        console.print(
            "Create one with: roadmap milestone create 'Milestone name' --due-date YYYY-MM-DD",
            style="dim",
        )

    @staticmethod
    def show_milestones_list(
        milestones_data: dict,
        get_due_date_status_fn,
    ) -> None:
        """Display list of milestones.

        Args:
            milestones_data: Dictionary with milestones, progress, estimates, etc.
            get_due_date_status_fn: Function to get due date string and styling
        """
        if not milestones_data["has_data"]:
            MilestoneListPresenter.show_empty_state()
            return

        # Display table
        MilestoneTablePresenter.display_milestone_table(
            milestones_data["milestones"],
            milestones_data["progress"],
            milestones_data["estimates"],
            get_due_date_status_fn,
        )

    @staticmethod
    def show_error(error_msg: str) -> None:
        """Display error message.

        Args:
            error_msg: Error message to display
        """
        console.print(
            f"❌ Failed to list milestones: {error_msg}",
            style="bold red",
        )
