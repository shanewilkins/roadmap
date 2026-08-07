"""Today command - daily workflow summary."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.presentation.daily_summary_presenter import (
    DailySummaryPresenter,
)
from roadmap.adapters.cli.services.daily_summary_service import DailySummaryService
from roadmap.common.console import get_console
from roadmap.common.logging import verbose_output

console = get_console()


@click.command("today")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@require_initialized
@verbose_output
def today(ctx: click.Context, verbose: bool = False):  # noqa: F841
    """Show your daily workflow summary for the upcoming milestone.

    Displays your assigned issues for the next upcoming milestone:
    - Current in-progress issues assigned to you
    - Overdue issues
    - High-priority tasks to start
    - Today's completed work

    Only shows issues assigned to you in the upcoming milestone.

    Example:
        roadmap today
    """
    core = ctx.obj["core"]

    try:
        # Use service to get daily summary data
        service = DailySummaryService(core)
        data = service.get_daily_summary_data()

        # Use presenter to render the data
        presenter = DailySummaryPresenter()
        presenter.render(data)

    except ValueError as e:
        console.print(f"❌ {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate daily summary: {e}", style="bold red")
        import traceback

        console.print(traceback.format_exc(), style="dim")
