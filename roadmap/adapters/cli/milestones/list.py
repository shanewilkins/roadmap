"""List milestones command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.decorators import with_output_support
from roadmap.adapters.cli.services.milestone_list_service import MilestoneListService
from roadmap.common.console import get_console
from roadmap.common.formatters import MilestoneTableFormatter
from roadmap.common.models import ColumnType
from roadmap.infrastructure.logging import verbose_output


def _get_console():
    """Get console instance at runtime to respect Click's test environment."""
    return get_console()


@click.command("list")
@click.option("--overdue", is_flag=True, help="Show only overdue milestones")
@click.pass_context
@with_output_support(
    available_columns=[
        "name",
        "description",
        "status",
        "due_date",
        "progress",
        "estimate",
    ],
    column_types={
        "name": ColumnType.STRING,
        "description": ColumnType.STRING,
        "status": ColumnType.ENUM,
        "due_date": ColumnType.DATE,
        "progress": ColumnType.STRING,
        "estimate": ColumnType.STRING,
    },
)
@require_initialized
@verbose_output
def list_milestones(ctx: click.Context, overdue: bool):
    """List all milestones.

    Supports output formatting with --format, --columns, --sort-by, --filter flags.
    """
    core = ctx.obj["core"]

    try:
        # Use MilestoneListService to get and filter milestones
        service = MilestoneListService(core)
        milestones_data = service.get_milestones_list_data(overdue_only=overdue)

        # Extract milestone list from service response
        milestone_list = milestones_data.get("milestones", [])

        # Handle empty result
        if not milestone_list:
            _get_console().print("📋 No milestones found.", style="yellow")
            _get_console().print(
                "Create one with: roadmap milestone create 'Milestone name' --due-date YYYY-MM-DD",
                style="dim",
            )
            return

        # Convert to TableData for structured output
        description = "overdue" if overdue else "all"
        table_data = MilestoneTableFormatter.milestones_to_table_data(
            milestone_list,
            title="Milestones",
            description=description,
            estimates=milestones_data.get("estimates", {}),
        )

        return table_data

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="list_milestones",
            entity_type="milestone",
            entity_id="all",
            context={"overdue": overdue},
            fatal=True,
        )
        _get_console().print(f"❌ Error listing milestones: {str(e)}", style="bold red")
