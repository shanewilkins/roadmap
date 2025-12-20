"""Show roadmap status and system health."""

import click
from structlog import get_logger

from roadmap.adapters.cli.health.scan import scan as health_scan
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.cli.presentation.core_initialization_presenter import (
    CoreInitializationPresenter,
)
from roadmap.adapters.cli.presentation.project_status_presenter import (
    IssueStatusPresenter,
    MilestoneProgressPresenter,
    RoadmapStatusPresenter,
)
from roadmap.adapters.cli.services.project_status_service import (
    IssueStatisticsService,
    MilestoneProgressService,
    StatusDataService,
)
from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.health import HealthCheck

logger = get_logger()
presenter = CoreInitializationPresenter()


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@require_initialized
def status(ctx: click.Context, verbose: bool) -> None:
    """Show the current status of the roadmap."""
    log = logger.bind(operation="status")
    log.info("starting_status")

    core = ctx.obj["core"]

    try:
        RoadmapStatusPresenter.show_status_header()

        # Gather status data
        status_data = StatusDataService.gather_status_data(core)
        log.info(
            "status_data_retrieved",
            issue_count=status_data["issue_count"],
            milestone_count=status_data["milestone_count"],
        )

        if not status_data["has_data"]:
            RoadmapStatusPresenter.show_empty_state()
            return

        # Compute milestone progress
        milestone_progress = MilestoneProgressService.get_all_milestones_progress(
            core, status_data["milestones"]
        )
        status_data["milestone_progress"] = milestone_progress

        # Compute issue statistics
        issue_counts = IssueStatisticsService.get_all_status_counts(
            status_data["issues"]
        )
        status_data["issue_counts"] = issue_counts

        # Show milestone progress
        if status_data["milestones"]:
            MilestoneProgressPresenter.show_all_milestones(
                status_data["milestones"],
                status_data["milestone_progress"],
            )

        # Show issues by status
        IssueStatusPresenter.show_all_issue_statuses(status_data["issue_counts"])

    except Exception as e:
        log.exception("status_error", error=str(e))
        RoadmapStatusPresenter.show_error(str(e))


def _extract_check_status(check_result) -> tuple:
    """Extract status and message from check result in any format.

    Returns:
        Tuple of (status, message)
    """
    if isinstance(check_result, tuple):
        return check_result
    return check_result.get("status", HealthStatus.UNHEALTHY), check_result.get(
        "message", ""
    )


def _get_status_display_info(status_str: str) -> tuple:
    """Get icon and color for a status string.

    Returns:
        Tuple of (icon, color_name)
    """
    status_map = {
        "HEALTHY": ("✅", "green"),
        "DEGRADED": ("⚠️", "yellow"),
        "UNHEALTHY": ("❌", "red"),
    }
    return status_map.get(status_str, ("?", "white"))


def _display_check_result(check_name: str, status: str, message: str):
    """Display a single health check result."""
    display_name = check_name.replace("_", " ").title()
    icon, color = _get_status_display_info(status)
    click.secho(f"{icon} {display_name}: {status}", fg=color)
    if message:
        click.echo(f"  {message}")


def _determine_overall_health(checks: dict) -> HealthStatus:
    """Determine overall health status from individual checks.

    Returns:
        Overall HealthStatus
    """
    overall_status = HealthStatus.HEALTHY

    for _check_name, check_result in checks.items():
        status = (
            check_result[0]
            if isinstance(check_result, tuple)
            else check_result.get("status")
        )

        if status == HealthStatus.UNHEALTHY:
            return HealthStatus.UNHEALTHY
        elif status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED

    return overall_status


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information and all health check logs",
)
@click.pass_context
def check_health(ctx: click.Context, verbose: bool) -> None:
    """Check system health and component status.

    By default, shows a summary of health checks with status indicators
    and suppresses debug logging output for a clean display.

    Use --verbose to see all debug logs and detailed check information.
    """
    log = logger.bind(operation="health")
    log.info("starting_health_check", verbose=verbose)

    core = ctx.obj["core"]

    presenter.present_health_header()

    try:
        # Run all health checks
        health_check = HealthCheck()
        checks = health_check.run_all_checks(core)

        # Display results
        click.echo()
        for check_name, check_result in checks.items():
            status, message = _extract_check_status(check_result)
            status_str = status.name if hasattr(status, "name") else str(status)
            _display_check_result(check_name, status_str, message)

        # Determine and display overall status
        overall_status = _determine_overall_health(checks)
        presenter.present_overall_health(overall_status)
        log.info("health_check_completed", status=overall_status)

    except Exception as e:
        log.exception("health_check_error", error=str(e))
        click.secho(f"❌ Health check failed: {e}", fg="red", bold=True)


# Create health group for health-related commands
@click.group(invoke_without_command=True)
@click.pass_context
def health(ctx: click.Context) -> None:
    """Health and diagnostics commands.

    Provides infrastructure health checks and entity-level diagnostics.

    If no subcommand is specified, runs the health check (default behavior).
    """
    if ctx.obj is None:
        ctx.obj = {}

    # If no subcommand was invoked, run 'check' by default
    if ctx.invoked_subcommand is None:
        # Invoke the check_health command with the same context
        ctx.invoke(check_health)


# Register health subcommands
health.add_command(check_health, name="check")
health.add_command(health_scan, name="scan")
