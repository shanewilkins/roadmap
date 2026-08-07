"""CLI command for displaying and querying sync metrics.

This module provides commands to view sync operation metrics,
historical data, and aggregate statistics.
"""

import click
from rich.panel import Panel

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.persistence.sync_metrics_repository import (
    SyncMetricsRepository,
)
from roadmap.common.console import get_console
from roadmap.presentation.formatters.sync_metrics_formatter import (
    create_metrics_history_table,
    create_metrics_summary_table,
)


@click.command(name="metrics")
@click.option(
    "--backend",
    type=str,
    default=None,
    help="Filter metrics by backend type (e.g., github, vanilla_git)",
)
@click.option(
    "--days",
    type=int,
    default=7,
    help="Show metrics from the last N days (default: 7)",
)
@click.option(
    "--latest",
    is_flag=True,
    help="Show only the latest sync metrics",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show aggregate statistics for the period",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed metrics including performance data",
)
@click.pass_context
@require_initialized
def sync_metrics(
    ctx: click.Context,
    backend: str | None,
    days: int,
    latest: bool,
    stats: bool,
    verbose: bool,
) -> None:
    r"""Display sync operation metrics and history.

    View historical sync metrics, performance data, and statistics
    to monitor sync health and performance over time.

    Examples:
    \b
        # Show metrics from last 7 days
        roadmap sync metrics

    \b
        # Show metrics from last 30 days for GitHub
        roadmap sync metrics --backend github --days 30

    \b
        # Show only the latest sync
        roadmap sync metrics --latest

    \b
        # Show aggregate statistics
        roadmap sync metrics --stats
    """
    console_inst = get_console()
    core = ctx.obj["core"]

    try:
        # Initialize repository with core's database manager
        metrics_repo = SyncMetricsRepository(core.db_manager)

        # Get metrics
        if latest:
            # Show only the latest sync
            metrics = metrics_repo.get_latest(backend_type=backend)
            if not metrics:
                console_inst.print("[yellow]No sync metrics found[/yellow]")
                return

            console_inst.print()
            console_inst.print(
                Panel(
                    create_metrics_summary_table(metrics, verbose),
                    title="[bold cyan]Latest Sync Metrics[/bold cyan]",
                    border_style="cyan",
                )
            )
            console_inst.print()

        elif stats:
            # Show aggregate statistics
            statistics = metrics_repo.get_statistics(backend_type=backend, days=days)

            if statistics and statistics["total_syncs"] > 0:
                from rich.table import Table

                stats_table = Table(show_header=False, box=None, padding=(0, 2))
                stats_table.add_column(style="bold")
                stats_table.add_column(justify="right", style="cyan")

                stats_table.add_row(
                    "Total Syncs",
                    str(statistics["total_syncs"]),
                )
                stats_table.add_row(
                    "Average Duration",
                    f"{statistics['avg_duration_seconds']:.1f}s",
                )
                stats_table.add_row(
                    "Total Duplicates",
                    str(statistics["total_duplicates_detected"]),
                )
                stats_table.add_row(
                    "Total Conflicts",
                    str(statistics["total_conflicts_detected"]),
                )
                stats_table.add_row(
                    "Total Errors",
                    str(statistics["total_errors"]),
                )

                console_inst.print()
                console_inst.print(
                    Panel(
                        stats_table,
                        title=f"[bold cyan]Statistics ({days} days)[/bold cyan]",
                        border_style="cyan",
                    )
                )
                console_inst.print()
            else:
                console_inst.print(
                    "[yellow]No sync metrics found for the specified period[/yellow]"
                )

        else:
            # Show history
            metrics_list = metrics_repo.list_by_date(backend_type=backend, days=days)

            if not metrics_list:
                console_inst.print(
                    f"[yellow]No sync metrics found in the last {days} days[/yellow]"
                )
                return

            console_inst.print()
            console_inst.print(
                Panel(
                    create_metrics_history_table(metrics_list, limit=10),
                    title=f"[bold cyan]Sync History (last {days} days)[/bold cyan]",
                    border_style="cyan",
                )
            )
            console_inst.print()

            # Show brief summary
            latest_metrics = metrics_list[0] if metrics_list else None
            if latest_metrics and verbose:
                console_inst.print(
                    Panel(
                        create_metrics_summary_table(latest_metrics, verbose),
                        title="[bold cyan]Latest Sync Details[/bold cyan]",
                        border_style="cyan",
                    )
                )
                console_inst.print()

    except Exception as e:
        console_inst.print(
            f"[bold red]❌ Error retrieving metrics: {str(e)}[/bold red]"
        )
        if verbose:
            raise
