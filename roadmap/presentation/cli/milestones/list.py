"""List milestones command."""

import click
from rich.table import Table

from roadmap.cli.utils import get_console

console = get_console()


@click.command("list")
@click.pass_context
def list_milestones(ctx: click.Context):
    """List all milestones."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        milestones = core.list_milestones()

        if not milestones:
            console.print("📋 No milestones found.", style="yellow")
            console.print(
                "Create one with: roadmap milestone create 'Milestone name'",
                style="dim",
            )
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Due Date", style="yellow", width=12)
        table.add_column("Status", style="green", width=10)
        table.add_column("Progress", style="blue", width=12)
        table.add_column("Estimate", style="green", width=10)

        # Get all issues for calculations
        all_issues = core.list_issues()

        for ms in milestones:
            progress = core.get_milestone_progress(ms.name)
            progress_text = f"{progress['completed']}/{progress['total']}"
            estimate_text = ms.get_estimated_time_display(all_issues)

            # Format due date
            due_date_text = ms.due_date.strftime("%Y-%m-%d") if ms.due_date else "-"

            # Add color coding for overdue milestones
            if ms.due_date:
                from datetime import datetime

                now = datetime.now().replace(tzinfo=None)  # Ensure timezone-naive
                ms_due_date = (
                    ms.due_date.replace(tzinfo=None)
                    if ms.due_date.tzinfo
                    else ms.due_date
                )

                if ms_due_date < now and ms.status.value == "open":
                    due_date_text = f"[bold red]{due_date_text}[/bold red]"
                elif (ms_due_date - now).days <= 7 and ms.status.value == "open":
                    due_date_text = f"[yellow]{due_date_text}[/yellow]"

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
        console.print(f"❌ Failed to list milestones: {e}", style="bold red")
