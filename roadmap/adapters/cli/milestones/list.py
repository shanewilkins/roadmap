"""List milestones command."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.cli.presentation.milestone_list_presenter import (
    MilestoneListPresenter,
)
from roadmap.adapters.cli.services.milestone_list_service import (
    MilestoneListService,
)
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import verbose_output


def _get_console():
    """Get console instance at runtime to respect Click's test environment."""
    return get_console()


@click.command("list")
@click.option("--overdue", is_flag=True, help="Show only overdue milestones")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@require_initialized
@verbose_output
def list_milestones(ctx: click.Context, overdue: bool, verbose: bool):
    """List all milestones."""
    core = ctx.obj["core"]

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
