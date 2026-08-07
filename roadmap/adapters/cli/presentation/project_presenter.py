"""CLI presenter for Project DTOs."""

from datetime import datetime

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from roadmap.adapters.cli.dtos import ProjectDTO
from roadmap.adapters.cli.presentation.base_presenter import BasePresenter
from roadmap.adapters.cli.presentation.table_builders import (
    create_list_table,
    create_metadata_table,
)
from roadmap.adapters.cli.styling import STATUS_COLORS


class ProjectPresenter(BasePresenter):
    """Presenter for formatting and displaying Project DTOs."""

    def render(
        self,
        project_dto: ProjectDTO,
        milestones: list | None = None,
        milestone_progress: dict | None = None,
        description_content: str | None = None,
        comments_text: str | None = None,
        effort_data: dict | None = None,
    ) -> None:
        """Render a project DTO in detailed view.

        Args:
            project_dto: The ProjectDTO to render
            milestones: Optional list of milestone objects to display
            milestone_progress: Optional progress information dict
            description_content: Optional content with description
            comments_text: Optional formatted comments text
            effort_data: Optional dict with 'estimated' and 'actual' hour counts
        """
        # Display header
        header = self._build_project_header(project_dto)
        self._get_console().print(Panel(header, border_style="cyan"))

        # Display metadata
        metadata = self._build_metadata_table(project_dto)
        self._get_console().print(
            Panel(metadata, title="📋 Details", border_style="blue")
        )

        # Display effort if provided
        if effort_data:
            effort = self._build_effort_table(effort_data)
            if effort:
                self._get_console().print(
                    Panel(effort, title="⏱️ Effort", border_style="yellow")
                )

        # Display milestones if provided
        if milestones:
            self._display_milestones_panel(milestones, milestone_progress)

        # Display description if provided
        if description_content:
            md = Markdown(description_content)
            self._get_console().print(
                Panel(md, title="📝 Description", border_style="white")
            )

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
            f"Created: {project_dto.created} • Updated: {project_dto.updated}"
        )
        self._get_console().print(f"\n[dim]{metadata_footer}[/dim]")

    def _build_project_header(self, project_dto: ProjectDTO) -> Text:
        """Build header text with project name and status.

        Args:
            project_dto: The ProjectDTO to format

        Returns:
            Rich Text object with formatted header
        """
        status_colors = {
            "planning": "blue",
            "active": "green",
            "on-hold": "yellow",
            "completed": "bold green",
            "cancelled": "red",
        }
        status_color = status_colors.get(project_dto.status, "white")

        header = Text()
        header.append(project_dto.name, style="bold white")
        header.append("\n")
        header.append(f"[{project_dto.status.upper()}]", style=f"bold {status_color}")

        return header

    def _build_metadata_table(self, project_dto: ProjectDTO):
        """Build metadata table for project DTO.

        Args:
            project_dto: The ProjectDTO to format

        Returns:
            Rich Table with metadata rows
        """
        metadata = create_metadata_table()

        metadata.add_row("Status", project_dto.status.upper())
        metadata.add_row("Owner", project_dto.owner or "Unassigned")

        if project_dto.headline:
            metadata.add_row("Headline", project_dto.headline)

        if isinstance(project_dto.target_end_date, datetime):
            metadata.add_row(
                "Target End Date", project_dto.target_end_date.strftime("%Y-%m-%d")
            )
        else:
            metadata.add_row("Target End Date", "Not set")

        if isinstance(project_dto.actual_end_date, datetime):
            metadata.add_row(
                "Actual End Date", project_dto.actual_end_date.strftime("%Y-%m-%d")
            )

        metadata.add_row("Milestones", str(project_dto.milestone_count))
        metadata.add_row("Issues", str(project_dto.issue_count))

        if isinstance(project_dto.created, datetime):
            metadata.add_row("Created", project_dto.created.strftime("%Y-%m-%d %H:%M"))

        if isinstance(project_dto.updated, datetime):
            metadata.add_row("Updated", project_dto.updated.strftime("%Y-%m-%d %H:%M"))

        return metadata

    def _build_effort_table(self, effort_data: dict):
        """Build effort/hours table if data exists.

        Args:
            effort_data: Dict with optional 'estimated' and 'actual' keys

        Returns:
            Rich Table with effort data or None if no data
        """
        if not (effort_data.get("estimated") or effort_data.get("actual")):
            return None

        effort = create_metadata_table()

        if effort_data.get("estimated"):
            estimated = effort_data["estimated"]
            if estimated < 8:
                estimated_display = f"{estimated:.1f}h"
            else:
                days = estimated / 8
                estimated_display = f"{days:.1f}d ({estimated:.1f}h)"
            effort.add_row("Estimated", estimated_display)

        if effort_data.get("actual"):
            actual = effort_data["actual"]
            if actual < 8:
                actual_display = f"{actual:.1f}h"
            else:
                days = actual / 8
                actual_display = f"{days:.1f}d ({actual:.1f}h)"
            effort.add_row("Actual", actual_display)

        return effort

    def _display_milestones_panel(
        self, milestones: list, _progress: dict | None = None
    ) -> None:
        """Display milestones in a table panel.

        Args:
            milestones: List of milestone objects
            _progress: Optional progress information dict (currently unused)
        """
        if not milestones:
            self._get_console().print(
                Panel(
                    "[dim]No milestones assigned to this project[/dim]",
                    title="🎯 Milestones",
                    border_style="magenta",
                )
            )
            return

        columns = [
            ("Name", "white", 25),
            ("Status", None, 11),
            ("Due Date", None, 11),
            ("Progress", None, 10),
        ]
        milestones_table = create_list_table(columns)

        for milestone in milestones[:10]:
            status_color = STATUS_COLORS.get(milestone.status.value, "white")
            due_date_str = (
                milestone.due_date.strftime("%Y-%m-%d")
                if hasattr(milestone.due_date, "strftime")
                else "Not set"
            )

            milestones_table.add_row(
                milestone.name,
                f"[{status_color}]{milestone.status.value}[/{status_color}]",
                due_date_str,
                f"{milestone.progress_percentage}%",
            )

        title = (
            f"🎯 Milestones (Showing 10 of {len(milestones)})"
            if len(milestones) > 10
            else "🎯 Milestones"
        )
        self._get_console().print(
            Panel(milestones_table, title=title, border_style="magenta")
        )
