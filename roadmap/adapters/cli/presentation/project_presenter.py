"""CLI presenter for Project DTOs."""

from datetime import datetime

from roadmap.adapters.cli.dtos import ProjectDTO
from roadmap.adapters.cli.presentation.base_presenter import BasePresenter
from roadmap.adapters.cli.presentation.table_builders import create_metadata_table
from roadmap.adapters.cli.styling import STATUS_COLORS
from rich.panel import Panel
from rich.text import Text


class ProjectPresenter(BasePresenter):
    """Presenter for formatting and displaying Project DTOs."""

    def render(self, project_dto: ProjectDTO) -> None:
        """Render a project DTO in detailed view.

        Args:
            project_dto: The ProjectDTO to render
        """
        # Display header
        header = self._build_project_header(project_dto)
        self._get_console().print(Panel(header, border_style="cyan"))

        # Display metadata
        metadata = self._build_metadata_table(project_dto)
        self._get_console().print(
            Panel(metadata, title="📋 Details", border_style="blue")
        )

    def _build_project_header(self, project_dto: ProjectDTO) -> Text:
        """Build header text with project name and status.

        Args:
            project_dto: The ProjectDTO to format

        Returns:
            Rich Text object with formatted header
        """
        status_color = STATUS_COLORS.get(project_dto.status, "white")

        header = Text()
        header.append(f"📦 {project_dto.name}", style="bold white")
        header.append("\n")
        header.append(
            f"[{project_dto.status.upper()}]", style=f"bold {status_color}"
        )

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

        if project_dto.description:
            metadata.add_row("Description", project_dto.description)

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
            metadata.add_row(
                "Created", project_dto.created.strftime("%Y-%m-%d %H:%M")
            )

        if isinstance(project_dto.updated, datetime):
            metadata.add_row(
                "Updated", project_dto.updated.strftime("%Y-%m-%d %H:%M")
            )

        return metadata
