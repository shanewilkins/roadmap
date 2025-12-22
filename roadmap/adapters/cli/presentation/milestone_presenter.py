"""CLI presenter for Milestone DTOs."""

from datetime import datetime

from roadmap.adapters.cli.dtos import MilestoneDTO
from roadmap.adapters.cli.presentation.base_presenter import BasePresenter
from roadmap.adapters.cli.presentation.table_builders import create_metadata_table
from roadmap.adapters.cli.styling import STATUS_COLORS
from rich.panel import Panel
from rich.text import Text


class MilestonePresenter(BasePresenter):
    """Presenter for formatting and displaying Milestone DTOs."""

    def render(self, milestone_dto: MilestoneDTO) -> None:
        """Render a milestone DTO in detailed view.

        Args:
            milestone_dto: The MilestoneDTO to render
        """
        # Display header
        header = self._build_milestone_header(milestone_dto)
        self._get_console().print(Panel(header, border_style="cyan"))

        # Display metadata
        metadata = self._build_metadata_table(milestone_dto)
        self._get_console().print(
            Panel(metadata, title="📋 Details", border_style="blue")
        )

    def _build_milestone_header(self, milestone_dto: MilestoneDTO) -> Text:
        """Build header text with milestone name and status.

        Args:
            milestone_dto: The MilestoneDTO to format

        Returns:
            Rich Text object with formatted header
        """
        status_color = STATUS_COLORS.get(milestone_dto.status, "white")

        header = Text()
        header.append(f"🎯 {milestone_dto.name}", style="bold white")
        header.append("\n")
        header.append(
            f"[{milestone_dto.status.upper()}]", style=f"bold {status_color}"
        )

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
