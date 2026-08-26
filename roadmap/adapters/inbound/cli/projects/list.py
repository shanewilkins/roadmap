"""List canonical projects with structured output."""

import click

from roadmap.adapters.inbound.cli.decorators import with_output_support
from roadmap.adapters.inbound.cli.models import ColumnDef, ColumnType, TableData


@click.command("list")
@click.option(
    "--status",
    type=click.Choice(["planning", "active", "on-hold", "completed", "cancelled"]),
)
@click.option("--owner")
@click.option("--priority", type=click.Choice(["critical", "high", "medium", "low"]))
@click.option("--overdue", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@with_output_support(
    available_columns=["id", "name", "status", "priority", "owner"],
    column_types={
        "id": ColumnType.STRING,
        "name": ColumnType.STRING,
        "status": ColumnType.ENUM,
        "priority": ColumnType.ENUM,
        "owner": ColumnType.STRING,
    },
)
def list_projects(
    ctx,
    status: str | None,
    owner: str | None,
    priority: str | None,
    overdue: bool,
    verbose: bool,
):  # noqa: ARG001
    """List projects from canonical documents."""
    planning = ctx.obj["core"].planning
    projects = [item.project for item in planning.snapshot().projects]
    projects = [
        item
        for item in projects
        if (status is None or item.status.value == status)
        and (owner is None or item.owner == owner)
        and (priority is None or item.priority.value == priority)
        and (not overdue or planning.project_is_overdue(item))
    ]
    columns = [
        ColumnDef("id", "ID"),
        ColumnDef("name", "Name"),
        ColumnDef("status", "Status", ColumnType.ENUM),
        ColumnDef("priority", "Priority", ColumnType.ENUM),
        ColumnDef("owner", "Owner"),
    ]
    return TableData(
        columns,
        [
            [
                str(item.id),
                str(item.name),
                item.status.value,
                item.priority.value,
                item.owner or "",
            ]
            for item in projects
        ],
        title="Projects",
        headline="filtered" if any((status, owner, priority, overdue)) else "all",
    )
