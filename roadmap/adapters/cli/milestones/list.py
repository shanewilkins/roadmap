"""List milestones command."""

import click

from roadmap.adapters.cli.decorators import with_output_support
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.output_models import ColumnType
from roadmap.infrastructure.logging import verbose_output
from roadmap.shared import MilestoneTableFormatter


def _get_console():
    """Get console instance at runtime to respect Click's test environment."""
    return get_console()


@click.command("list")
@click.option("--overdue", is_flag=True, help="Show only overdue milestones")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@with_output_support(
    available_columns=["name", "description", "status", "due_date", "progress"],
    column_types={
        "name": ColumnType.STRING,
        "description": ColumnType.STRING,
        "status": ColumnType.ENUM,
        "due_date": ColumnType.DATE,
        "progress": ColumnType.STRING,
    },
)
@require_initialized
@verbose_output
def list_milestones(ctx: click.Context, overdue: bool, verbose: bool):
    """List all milestones.

    Supports output formatting with --format, --columns, --sort-by, --filter flags.
    """
    core = ctx.obj["core"]

    try:
        # Get all milestones
        milestones = core.milestones.list()

        # Filter by overdue if requested
        if overdue:
            from datetime import datetime

            now = datetime.now()
            milestones = [
                m
                for m in milestones
                if hasattr(m, "due_date")
                and m.due_date
                and m.due_date < now
                and (not hasattr(m, "status") or m.status.value != "closed")
            ]

        # Handle empty result
        if not milestones:
            _get_console().print("📋 No milestones found.", style="yellow")
            _get_console().print(
                "Create one with: roadmap milestone create 'Milestone name' --due-date YYYY-MM-DD",
                style="dim",
            )
            return

        # Convert to TableData for structured output
        description = "overdue" if overdue else "all"
        table_data = MilestoneTableFormatter.milestones_to_table_data(
            milestones,
            title="Milestones",
            description=description,
        )

        return table_data

    except Exception as e:
        _get_console().print(f"❌ Error listing milestones: {str(e)}", style="bold red")
