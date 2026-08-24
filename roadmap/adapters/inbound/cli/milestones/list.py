"""List canonical milestones with derived progress."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.decorators import with_output_support
from roadmap.adapters.inbound.cli.instrumentation import verbose_output
from roadmap.adapters.inbound.cli.models import ColumnDef, ColumnType, TableData


@click.command("list")
@click.option("--overdue", is_flag=True)
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
def list_milestones(ctx, overdue: bool):
    """List milestones from canonical documents."""
    planning = ctx.obj["core"].planning
    summaries = [
        item
        for item in planning.snapshot().milestones
        if not overdue or planning.milestone_is_overdue(item.milestone)
    ]
    columns = [
        ColumnDef("name", "Name"),
        ColumnDef("description", "Description"),
        ColumnDef("status", "Status", ColumnType.ENUM),
        ColumnDef("due_date", "Due date", ColumnType.DATE),
        ColumnDef("progress", "Progress"),
        ColumnDef("estimate", "Estimate"),
    ]
    return TableData(
        columns,
        [
            [
                str(item.milestone.name),
                item.milestone.headline,
                item.milestone.status.value,
                item.milestone.due_at.value.date().isoformat()
                if item.milestone.due_at
                else "",
                f"{item.progress:.1f}%",
                f"{item.estimated_hours:.1f}h",
            ]
            for item in summaries
        ],
        title="Milestones",
        headline="overdue" if overdue else "all",
    )
