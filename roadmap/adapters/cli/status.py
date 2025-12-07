"""Show roadmap status and system health."""

import click
from structlog import get_logger

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
from roadmap.infrastructure.health import HealthCheck, HealthStatus

logger = get_logger()
presenter = CoreInitializationPresenter()


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
def status(ctx: click.Context, verbose: bool) -> None:
    """Show the current status of the roadmap."""
    log = logger.bind(operation="status")
    log.info("starting_status")

    core = ctx.obj["core"]

    if not core.is_initialized():
        log.warning("roadmap_not_initialized")
        click.secho(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            fg="red",
            bold=True,
        )
        return

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


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information and all health check logs",
)
@click.pass_context
def health(ctx: click.Context, verbose: bool) -> None:
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
            # Handle tuple format (status, message)
            if isinstance(check_result, tuple):
                status, message = check_result
            else:
                status = check_result.get("status", HealthStatus.UNHEALTHY)
                message = check_result.get("message", "")

            # Format check name and display
            display_name = check_name.replace("_", " ").title()

            # Map status to display values
            status_str = status.name if hasattr(status, "name") else str(status)
            status_map = {
                "HEALTHY": ("✅", "green"),
                "DEGRADED": ("⚠️", "yellow"),
                "UNHEALTHY": ("❌", "red"),
            }

            icon, color = status_map.get(status_str, ("?", "white"))
            click.secho(f"{icon} {display_name}: {status_str}", fg=color)
            if message:
                click.echo(f"  {message}")

        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        if checks:
            for _check_name, check_result in checks.items():
                status = (
                    check_result[0]
                    if isinstance(check_result, tuple)
                    else check_result.get("status")
                )
                if status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                elif (
                    status == HealthStatus.DEGRADED
                    and overall_status == HealthStatus.HEALTHY
                ):
                    overall_status = HealthStatus.DEGRADED

        # Display overall status
        presenter.present_overall_health(overall_status)
        log.info("health_check_completed", status=overall_status)

    except Exception as e:
        log.exception("health_check_error", error=str(e))
        click.secho(f"❌ Health check failed: {e}", fg="red", bold=True)
