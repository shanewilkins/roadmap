"""Daily summary presenter for formatting and rendering output.

Handles all display formatting for the daily summary, including
table rendering and output styling.
"""

from datetime import UTC, datetime

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.adapters.cli.presentation.base_presenter import BasePresenter
from roadmap.common.console import get_console

console = get_console()


class DailySummaryPresenter(BasePresenter):
    """Presenter for daily summary output.

    Handles formatting and rendering of daily summary data
    including tables, panels, and styling.
    """

    def render(self, data: dict) -> None:
        """Render complete daily summary to console.

        Args:
            data: Dictionary from DailySummaryService.get_daily_summary_data()
        """
        if not data["has_issues"]:
            milestone = data["milestone"]
            console.print(
                f"✅ No issues assigned to you in [bold]{milestone.name}[/bold]",
                style="green",
            )
            return

        # Render header
        self._render_header(data)

        # Render sections
        issues = data["issues"]
        self._render_in_progress(issues["in_progress"])
        self._render_overdue(issues["overdue"])
        self._render_blocked(issues["blocked"])
        self._render_up_next(issues["todo_high_priority"])
        self._render_completed_today(issues["completed_today"])

        # Render summary and tips
        self._render_summary(issues)
        self._render_tips(data)

    @staticmethod
    def _render_header(data: dict) -> None:
        """Render daily summary header with user and milestone info."""
        current_user = data["current_user"]
        milestone = data["milestone"]

        header = Text()
        header.append("Daily Summary - ", style="dim")
        header.append(current_user, style="bold cyan")
        header.append("\nMilestone: ", style="dim")
        header.append(milestone.name, style="bold yellow")

        if milestone.due_date:
            header.append(
                f" (due {milestone.due_date.strftime('%Y-%m-%d')})",
                style="dim",
            )

        header.append(f"\n{datetime.now(UTC).strftime('%A, %B %d, %Y')}", style="dim")

        console.print(Panel(header, border_style="cyan"))

    @staticmethod
    def _render_in_progress(issues: list) -> None:
        """Render in-progress issues section."""
        if issues:
            progress_table = Table(
                show_header=True,
                header_style="bold yellow",
                title="🚀 In Progress",
                title_style="bold yellow",
            )
            progress_table.add_column("ID", style="cyan", width=10)
            progress_table.add_column("Title", style="white")
            progress_table.add_column("Progress", width=12)
            progress_table.add_column("Priority", width=10)

            for issue in issues:
                progress_table.add_row(
                    issue.id,
                    issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
                    issue.progress_display,
                    issue.priority.value,
                )

            console.print(progress_table)
            console.print()
        else:
            console.print(
                Panel(
                    "[dim]No issues currently in progress[/dim]",
                    title="🚀 In Progress",
                    title_align="left",
                    border_style="yellow",
                )
            )
            console.print()

    @staticmethod
    def _render_overdue(issues: list) -> None:
        """Render overdue issues section."""
        if issues:
            overdue_table = Table(
                show_header=True,
                header_style="bold red",
                title="⚠️  Overdue",
                title_style="bold red",
            )
            overdue_table.add_column("ID", style="cyan", width=10)
            overdue_table.add_column("Title", style="white")
            overdue_table.add_column("Due Date", width=12, style="red")
            overdue_table.add_column("Priority", width=10)

            for issue in issues:
                due_date_obj = issue.due_date
                # Normalize issue due_date to UTC-aware datetime
                if isinstance(due_date_obj, datetime):
                    if due_date_obj.tzinfo:
                        due_date_aware = due_date_obj.astimezone(UTC)
                    else:
                        due_date_aware = due_date_obj.replace(tzinfo=UTC)
                else:
                    due_date_aware = datetime.fromisoformat(str(due_date_obj)).replace(
                        tzinfo=UTC
                    )

                days_overdue = (datetime.now(UTC) - due_date_aware).days
                overdue_table.add_row(
                    issue.id,
                    issue.title[:50] + "..." if len(issue.title) > 50 else issue.title,
                    f"{due_date_aware.strftime('%Y-%m-%d')} ({days_overdue}d)",
                    issue.priority.value,
                )

            console.print(overdue_table)
            console.print()

    @staticmethod
    def _render_blocked(issues: list) -> None:
        """Render blocked issues section."""
        if issues:
            blocked_table = Table(
                show_header=True,
                header_style="bold red",
                title="🚫 Blocked",
                title_style="bold red",
            )
            blocked_table.add_column("ID", style="cyan", width=10)
            blocked_table.add_column("Title", style="white")
            blocked_table.add_column("Priority", width=10)

            for issue in issues:
                blocked_table.add_row(
                    issue.id,
                    issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
                    issue.priority.value,
                )

            console.print(blocked_table)
            console.print()

    @staticmethod
    def _render_up_next(issues: list) -> None:
        """Render up next (high priority todos) section."""
        if issues:
            next_table = Table(
                show_header=True,
                header_style="bold blue",
                title="📋 Up Next (High Priority)",
                title_style="bold blue",
            )
            next_table.add_column("ID", style="cyan", width=10)
            next_table.add_column("Title", style="white")
            next_table.add_column("Priority", width=10)
            next_table.add_column("Estimate", width=10)

            for issue in issues:
                priority_color = (
                    "bold red" if issue.priority.value == "critical" else "red"
                )
                next_table.add_row(
                    issue.id,
                    issue.title[:55] + "..." if len(issue.title) > 55 else issue.title,
                    f"[{priority_color}]{issue.priority.value}[/{priority_color}]",
                    issue.estimated_time_display,
                )

            console.print(next_table)
            console.print()

    @staticmethod
    def _render_completed_today(issues: list) -> None:
        """Render completed today section."""
        if issues:
            done_table = Table(
                show_header=True,
                header_style="bold green",
                title="✅ Completed Today",
                title_style="bold green",
            )
            done_table.add_column("ID", style="cyan", width=10)
            done_table.add_column("Title", style="white")
            done_table.add_column("Completed", width=12)

            for issue in issues:
                done_table.add_row(
                    issue.id,
                    issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
                    issue.actual_end_date.strftime("%H:%M"),
                )

            console.print(done_table)
            console.print()

    @staticmethod
    def _render_summary(issues: dict) -> None:
        """Render summary footer with counters."""
        summary = Text()
        summary.append("\n📊 Summary: ", style="bold")
        summary.append(f"{len(issues['in_progress'])} in progress", style="yellow")
        summary.append(" • ", style="dim")

        overdue_style = "red" if issues["overdue"] else "dim"
        summary.append(f"{len(issues['overdue'])} overdue", style=overdue_style)
        summary.append(" • ", style="dim")

        blocked_style = "red" if issues["blocked"] else "dim"
        summary.append(f"{len(issues['blocked'])} blocked", style=blocked_style)
        summary.append(" • ", style="dim")
        summary.append(
            f"{len(issues['completed_today'])} completed today", style="green"
        )

        console.print(summary)

    @staticmethod
    def _render_tips(data: dict) -> None:
        """Render helpful tips based on data."""
        issues = data["issues"]

        if not issues["in_progress"] and issues["todo_high_priority"]:
            issue = issues["todo_high_priority"][0]
            console.print(
                f"\n💡 Tip: Start work on an issue with: [cyan]roadmap issue start {issue.id}[/cyan]",
                style="dim",
            )
        elif issues["overdue"]:
            issue = issues["overdue"][0]
            console.print(
                f"\n💡 Tip: View overdue issue details with: [cyan]roadmap issue view {issue.id}[/cyan]",
                style="dim",
            )
