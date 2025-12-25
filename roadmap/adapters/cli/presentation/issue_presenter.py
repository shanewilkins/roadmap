"""CLI presenter for Issue DTOs."""

from datetime import datetime

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from roadmap.adapters.cli.dtos import IssueDTO
from roadmap.adapters.cli.presentation.base_presenter import BasePresenter
from roadmap.adapters.cli.presentation.table_builders import create_metadata_table
from roadmap.adapters.cli.styling import PRIORITY_COLORS, STATUS_COLORS


class IssuePresenter(BasePresenter):
    """Presenter for formatting and displaying Issue DTOs."""

    def render(self, issue_dto: IssueDTO) -> None:
        """Render an issue DTO in detailed view.

        Args:
            issue_dto: The IssueDTO to render
        """
        # Display header
        header = self._build_issue_header(issue_dto)
        self._get_console().print(Panel(header, border_style="cyan"))

        # Display metadata
        metadata = self._build_metadata_table(issue_dto)
        self._get_console().print(
            Panel(metadata, title="📋 Metadata", border_style="blue")
        )

        # Display timeline
        timeline = self._build_timeline_table(issue_dto)
        self._get_console().print(
            Panel(timeline, title="⏱️  Timeline", border_style="yellow")
        )

        # Display dependencies if any
        deps = self._build_dependencies_table(issue_dto)
        if deps:
            self._get_console().print(
                Panel(deps, title="🔗 Dependencies", border_style="magenta")
            )

        # Display description if available
        if issue_dto.content:
            description, acceptance = self._extract_description_and_criteria(
                issue_dto.content
            )

            if description:
                md = Markdown(description)
                self._get_console().print(
                    Panel(md, title="📝 Description", border_style="white")
                )

            if acceptance:
                md = Markdown(acceptance)
                self._get_console().print(
                    Panel(md, title="✅ Acceptance Criteria", border_style="green")
                )
        else:
            self._get_console().print(
                Panel(
                    "[dim]No description available[/dim]",
                    title="📝 Description",
                    border_style="white",
                )
            )

    def _build_issue_header(self, issue_dto: IssueDTO) -> Text:
        """Build header text with issue title and metadata.

        Args:
            issue_dto: The IssueDTO to format

        Returns:
            Rich Text object with formatted header
        """
        status_color = STATUS_COLORS.get(issue_dto.status, "white")
        priority_color = PRIORITY_COLORS.get(issue_dto.priority, "white")

        header = Text()
        header.append(f"#{issue_dto.id}", style="bold cyan")
        header.append(" • ", style="dim")
        header.append(issue_dto.title, style="bold white")
        header.append("\n")
        header.append(f"[{issue_dto.status.upper()}]", style=f"bold {status_color}")
        header.append(" • ", style="dim")
        header.append(issue_dto.priority.upper(), style=priority_color)
        header.append(" • ", style="dim")
        header.append(issue_dto.issue_type.title(), style="cyan")

        return header

    def _build_metadata_table(self, issue_dto: IssueDTO):
        """Build metadata table for issue DTO.

        Args:
            issue_dto: The IssueDTO to format

        Returns:
            Rich Table with metadata rows
        """
        metadata = create_metadata_table()

        metadata.add_row("Assignee", issue_dto.assignee or "Unassigned")
        metadata.add_row("Milestone", issue_dto.milestone or "None")
        if issue_dto.created:
            metadata.add_row("Created", issue_dto.created.strftime("%Y-%m-%d %H:%M"))
        if issue_dto.updated:
            metadata.add_row("Updated", issue_dto.updated.strftime("%Y-%m-%d %H:%M"))

        if issue_dto.labels:
            metadata.add_row("Labels", ", ".join(issue_dto.labels))

        if issue_dto.github_issue:
            github_id = (
                f"#{issue_dto.github_issue}"
                if isinstance(issue_dto.github_issue, int)
                else str(issue_dto.github_issue)
            )
            metadata.add_row("GitHub Issue", github_id)

        return metadata

    def _build_timeline_table(self, issue_dto: IssueDTO):
        """Build timeline table for issue DTO.

        Args:
            issue_dto: The IssueDTO to format

        Returns:
            Rich Table with timeline rows
        """
        timeline = create_metadata_table()

        # Display estimated hours
        if issue_dto.estimated_hours:
            timeline.add_row("Estimated", f"{issue_dto.estimated_hours:.1f}h")
        else:
            timeline.add_row("Estimated", "Not estimated")

        # Display progress
        if issue_dto.progress_percentage is not None:
            timeline.add_row("Progress", f"{issue_dto.progress_percentage}%")
        else:
            timeline.add_row("Progress", "0%")

        # Display end date if present
        if isinstance(issue_dto.actual_end_date, datetime):
            timeline.add_row(
                "Completed", issue_dto.actual_end_date.strftime("%Y-%m-%d %H:%M")
            )

        # Display due date if present
        if isinstance(issue_dto.due_date, datetime):
            timeline.add_row("Due Date", issue_dto.due_date.strftime("%Y-%m-%d"))

        return timeline

    def _build_dependencies_table(self, issue_dto: IssueDTO):
        """Build dependencies table if exists.

        Args:
            issue_dto: The IssueDTO to format

        Returns:
            Rich Table with dependencies or None if no dependencies
        """
        # For now, DTOs don't store dependencies - would need to extend model
        return None

    def _extract_description_and_criteria(self, content: str) -> tuple[str, str]:
        """Parse issue content to extract description and acceptance criteria.

        Args:
            content: The issue content/description text

        Returns:
            Tuple of (description, acceptance_criteria) strings
        """
        content_lines = content.split("\n")
        description_lines = []
        acceptance_lines = []
        in_acceptance = False

        for line in content_lines:
            if (
                "## Acceptance Criteria" in line
                or "## acceptance criteria" in line.lower()
            ):
                in_acceptance = True
                continue
            elif line.startswith("## ") and in_acceptance:
                in_acceptance = False

            if in_acceptance:
                acceptance_lines.append(line)
            elif not line.startswith("#"):
                description_lines.append(line)

        description = "\n".join(description_lines).strip()
        acceptance = "\n".join(acceptance_lines).strip()

        return description, acceptance
