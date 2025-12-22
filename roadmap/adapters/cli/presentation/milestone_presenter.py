"""CLI presenter for Milestone DTOs."""

from datetime import datetime

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from roadmap.adapters.cli.dtos import MilestoneDTO
from roadmap.adapters.cli.presentation.base_presenter import BasePresenter
from roadmap.adapters.cli.presentation.table_builders import (
    create_list_table,
    create_metadata_table,
)
from roadmap.adapters.cli.styling import PRIORITY_COLORS, STATUS_COLORS


class MilestonePresenter(BasePresenter):
    """Presenter for formatting and displaying Milestone DTOs."""

    def render(
        self,
        milestone_dto: MilestoneDTO,
        issues: list | None = None,
        progress_data: dict | None = None,
        description_content: str | None = None,
        comments_text: str | None = None,
    ) -> None:
        """Render a milestone DTO in detailed view.

        Args:
            milestone_dto: The MilestoneDTO to render
            issues: Optional list of issues to display
            progress_data: Optional progress information dict with 'completed' and 'total' keys
            description_content: Optional content with description and goals
            comments_text: Optional formatted comments text
        """
        # Display header
        header = self._build_milestone_header(milestone_dto)
        self._get_console().print(Panel(header, border_style="cyan"))

        # Display progress if provided
        if progress_data:
            self._display_progress_panel(progress_data)

        # Display metadata
        metadata = self._build_metadata_table(milestone_dto)
        self._get_console().print(
            Panel(metadata, title="📈 Statistics", border_style="blue")
        )

        # Display issues if provided
        if issues is not None:
            self._display_issues_panel(issues)

        # Display description and goals if provided
        if description_content:
            self._display_description_and_goals(description_content)

        # Display comments if provided
        if comments_text:
            self._get_console().print(
                Panel(
                    comments_text,
                    title="💬 Comments",
                    border_style="cyan",
                )
            )

        # Display metadata footer
        metadata_footer = (
            f"Created: {milestone_dto.created} • " f"Updated: {milestone_dto.updated}"
        )
        self._get_console().print(f"\n[dim]{metadata_footer}[/dim]")

    def _build_milestone_header(self, milestone_dto: MilestoneDTO) -> Text:
        """Build header text with milestone name and status.

        Args:
            milestone_dto: The MilestoneDTO to format

        Returns:
            Rich Text object with formatted header
        """
        status_color = "green" if milestone_dto.status == "closed" else "yellow"

        header = Text()
        header.append(milestone_dto.name, style="bold cyan")
        header.append("\n")
        header.append(f"[{milestone_dto.status.upper()}]", style=f"bold {status_color}")

        # Add due date if present
        if milestone_dto.due_date:
            due_date_str = (
                milestone_dto.due_date.strftime("%Y-%m-%d")
                if hasattr(milestone_dto.due_date, "strftime")
                else milestone_dto.due_date
            )
            now = datetime.now()

            due_date_obj = (
                milestone_dto.due_date
                if hasattr(milestone_dto.due_date, "replace")
                else datetime.fromisoformat(str(milestone_dto.due_date))
            )
            due_date_naive = (
                due_date_obj.replace(tzinfo=None)
                if due_date_obj.tzinfo
                else due_date_obj
            )
            is_overdue = due_date_naive < now and milestone_dto.status == "open"

            header.append(" • ", style="dim")
            if is_overdue:
                days_overdue = (now - due_date_naive).days
                header.append(f"⚠️  OVERDUE by {days_overdue} days", style="bold red")
                header.append(f" (Due: {due_date_str})", style="red")
            else:
                header.append(f"Due: {due_date_str}", style="white")

        return header

    def _build_metadata_table(self, milestone_dto: MilestoneDTO):
        """Build metadata table for milestone DTO.

        Args:
            milestone_dto: The MilestoneDTO to format

        Returns:
            Rich Table with metadata rows
        """
        metadata = create_metadata_table()

        metadata.add_row("Status", milestone_dto.status.upper())

        if isinstance(milestone_dto.due_date, datetime):
            metadata.add_row("Due Date", milestone_dto.due_date.strftime("%Y-%m-%d"))
        else:
            metadata.add_row("Due Date", "Not set")

        if milestone_dto.description:
            metadata.add_row("Description", milestone_dto.description)

        metadata.add_row("Progress", f"{milestone_dto.progress_percentage}%")
        metadata.add_row(
            "Issues",
            f"{milestone_dto.completed_count}/{milestone_dto.issue_count}",
        )

        if isinstance(milestone_dto.created, datetime):
            metadata.add_row(
                "Created", milestone_dto.created.strftime("%Y-%m-%d %H:%M")
            )

        if isinstance(milestone_dto.updated, datetime):
            metadata.add_row(
                "Updated", milestone_dto.updated.strftime("%Y-%m-%d %H:%M")
            )

        return metadata

    def _display_progress_panel(self, progress_data: dict) -> None:
        """Display milestone progress as a panel.

        Args:
            progress_data: Dict with 'completed' and 'total' keys
        """
        completed = progress_data.get("completed", 0)
        total = progress_data.get("total", 0)
        percentage = (completed / total * 100) if total > 0 else 0

        progress_table = create_metadata_table()
        progress_table.add_row("Issues Complete", f"{completed}/{total}")
        progress_table.add_row("Percentage", f"{percentage:.1f}%")

        self._get_console().print(
            Panel(
                progress_table,
                title="📊 Progress",
                border_style="green" if percentage > 50 else "yellow",
            )
        )

    def _display_issues_panel(self, issues: list) -> None:
        """Display issues in a table panel.

        Args:
            issues: List of issue objects with status, priority, etc.
        """
        if not issues:
            self._get_console().print(
                Panel(
                    "[dim]No issues assigned to this milestone[/dim]",
                    title="📋 Issues",
                    border_style="magenta",
                )
            )
            return

        columns = [
            ("ID", "cyan", 9),
            ("Title", "white", 20),
            ("Status", None, 11),
            ("Priority", None, 9),
            ("Assignee", None, 12),
            ("Progress", None, 10),
            ("Estimate", None, 10),
        ]
        issues_table = create_list_table(columns)

        for issue in issues[:10]:
            status_color = STATUS_COLORS.get(issue.status.value, "white")
            priority_color = PRIORITY_COLORS.get(issue.priority.value, "white")
            assignee_display = (
                issue.assignee if issue.assignee else "[dim]Unassigned[/dim]"
            )

            issues_table.add_row(
                issue.id,
                issue.title[:50] + "..." if len(issue.title) > 50 else issue.title,
                f"[{status_color}]{issue.status.value}[/{status_color}]",
                f"[{priority_color}]{issue.priority.value}[/{priority_color}]",
                assignee_display,
                issue.progress_display,
                issue.estimated_time_display,
            )

        title = (
            f"📋 Issues (Showing 10 of {len(issues)})"
            if len(issues) > 10
            else "📋 Issues"
        )
        self._get_console().print(
            Panel(issues_table, title=title, border_style="magenta")
        )

    def _display_description_and_goals(self, content: str) -> None:
        """Display description and goals sections from content.

        Args:
            content: Raw content with markdown sections
        """
        description, goals = self._extract_description_and_goals(content)

        if description:
            md = Markdown(description)
            self._get_console().print(
                Panel(md, title="📝 Description", border_style="white")
            )

        if goals:
            md = Markdown(goals)
            self._get_console().print(Panel(md, title="🎯 Goals", border_style="green"))

    @staticmethod
    def _extract_description_and_goals(content: str) -> tuple[str, str]:
        """Parse content to extract description and goals sections.

        Args:
            content: Raw content string with markdown sections

        Returns:
            Tuple of (description, goals) strings
        """
        content_lines = content.split("\n")
        description_lines = []
        goals_lines = []
        in_goals = False

        for line in content_lines:
            if "## Goals" in line or "## goals" in line.lower():
                in_goals = True
                continue
            elif line.startswith("## ") and in_goals:
                in_goals = False

            if in_goals:
                goals_lines.append(line)
            elif not line.startswith("#"):
                description_lines.append(line)

        return "\n".join(description_lines).strip(), "\n".join(goals_lines).strip()
