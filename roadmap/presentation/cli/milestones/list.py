"""List milestones command."""

import click

from roadmap.presentation.cli.logging_decorators import verbose_output
from roadmap.presentation.cli.presentation.milestone_list_presenter import (
    MilestoneListPresenter,
)
from roadmap.presentation.cli.services.milestone_list_service import (
    MilestoneListService,
)
from roadmap.shared.console import get_console

console = get_console()


@click.command("list")
@click.option("--overdue", is_flag=True, help="Show only overdue milestones")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
def list_milestones(ctx: click.Context, overdue: bool, verbose: bool):
    """List all milestones."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Use service to get milestone list data
        service = MilestoneListService(core)
        milestones_data = service.get_milestones_list_data(overdue_only=overdue)

        # Use presenter to render the data
        MilestoneListPresenter.show_milestones_list(
            milestones_data,
            service.get_milestone_due_date_status,
        )

    except Exception as e:
        MilestoneListPresenter.show_error(str(e))
