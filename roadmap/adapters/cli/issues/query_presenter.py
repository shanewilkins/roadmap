"""Rich presentation of target issue query records."""

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.adapters.cli.styling import PRIORITY_COLORS, STATUS_COLORS
from roadmap.application.contracts import IssueQueryRecord
from roadmap.common.console import get_console


def _metadata() -> Table:
    table = Table(show_header=False, box=None)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    return table


class IssueQueryPresenter:
    def render(self, record: IssueQueryRecord) -> None:
        issue = record.issue
        status = issue.status.value
        priority = issue.priority.value
        header = Text()
        header.append(f"#{issue.id}", style="bold cyan")
        header.append(f" • {issue.title}\n", style="bold white")
        header.append(
            f"[{status.upper()}]",
            style=f"bold {STATUS_COLORS.get(status, 'white')}",
        )
        header.append(
            f" • {priority.upper()}", style=PRIORITY_COLORS.get(priority, "white")
        )
        header.append(f" • {issue.issue_type.value.title()}", style="cyan")
        console = get_console()
        console.print(Panel(header, border_style="cyan"))

        metadata = _metadata()
        metadata.add_row("Assignee", issue.assignee or "Unassigned")
        metadata.add_row(
            "Milestone",
            record.milestone_name or str(issue.relations.milestone_id or "None"),
        )
        metadata.add_row("Lifecycle", issue.retention.value)
        metadata.add_row("Created", issue.created.value.strftime("%Y-%m-%d %H:%M"))
        metadata.add_row("Updated", issue.updated.value.strftime("%Y-%m-%d %H:%M"))
        if issue.labels:
            metadata.add_row("Labels", ", ".join(issue.labels))
        console.print(Panel(metadata, title="📋 Metadata", border_style="blue"))

        timeline = _metadata()
        timeline.add_row(
            "Estimated",
            f"{issue.estimated_hours:.1f}h"
            if issue.estimated_hours is not None
            else "Not estimated",
        )
        timeline.add_row("Progress", f"{issue.progress_percentage or 0:g}%")
        if record.actual_end_at:
            timeline.add_row(
                "Completed", record.actual_end_at.value.strftime("%Y-%m-%d %H:%M")
            )
        if issue.due_at:
            timeline.add_row("Due Date", issue.due_at.value.strftime("%Y-%m-%d"))
        console.print(Panel(timeline, title="⏱️  Timeline", border_style="yellow"))

        if issue.relations.depends_on or issue.relations.blocks:
            dependencies = _metadata()
            if issue.relations.depends_on:
                dependencies.add_row(
                    "Depends on", ", ".join(issue.relations.depends_on)
                )
            if issue.relations.blocks:
                dependencies.add_row("Blocks", ", ".join(issue.relations.blocks))
            console.print(
                Panel(dependencies, title="🔗 Dependencies", border_style="magenta")
            )

        console.print(
            Panel(
                Markdown(issue.content)
                if issue.content
                else "[dim]No description available[/dim]",
                title="📝 Description",
                border_style="white",
            )
        )
        if record.comments:
            comments = Table(show_header=False, box=None, padding=(1, 0))
            comments.add_column("Comments")
            for comment in record.comments:
                comments.add_row(
                    f"[bold magenta]@{comment.author}[/bold magenta]"
                    f" [dim]· {comment.created_at.value:%Y-%m-%d %H:%M}[/dim]\n"
                    f"{comment.body}"
                )
            console.print(
                Panel(
                    comments,
                    title=f"💬 Comments ({len(record.comments)})",
                    border_style="cyan",
                )
            )
