"""Show roadmap status and system health."""

import json
from collections import Counter
from pathlib import Path

import click
from structlog import get_logger

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.health.db_integrity import db_integrity
from roadmap.adapters.cli.health.fixer import HealthFixOrchestrator
from roadmap.adapters.cli.health.formatter import HealthCheckFormatter
from roadmap.adapters.cli.health.scan import scan as health_scan
from roadmap.adapters.cli.output_manager import OutputManager
from roadmap.adapters.cli.presentation.core_initialization_presenter import (
    CoreInitializationPresenter,
)
from roadmap.adapters.cli.presentation.project_status_presenter import (
    RoadmapStatusPresenter,
)
from roadmap.adapters.cli.utils.click_options import (
    details_option,
    format_option,
    health_check_options,
    verbose_option,
)
from roadmap.common.models import ColumnDef, ColumnType, TableData
from roadmap.common.output_formatter import OutputFormatter
from roadmap.domain.types import (
    IssueStatus,
    MilestoneStatus,
    ProjectStatus,
    RetentionState,
)
from roadmap.infrastructure.observability.health import HealthCheck

logger = get_logger()
presenter = CoreInitializationPresenter()


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.option(
    "--format",
    "-f",
    type=click.Choice(
        ["rich", "plain", "json", "csv", "markdown"], case_sensitive=False
    ),
    default="rich",
    help="Output format (rich=default, plain=POSIX, json=machine-readable, csv=analysis)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Write output to file",
)
@click.pass_context
@require_initialized
def status(ctx: click.Context, verbose: bool, format: str, output: Path | None) -> None:
    """Show the current status of the roadmap."""
    log = logger.bind(operation="status")
    log.info("starting_status")

    core = ctx.obj["core"]

    try:
        format_name = (format or "rich").lower()
        if format_name == "rich":
            RoadmapStatusPresenter.show_status_header()
        elif format_name == "plain":
            click.echo("Roadmap Status")

        tables_by_name = _build_snapshot_tables(core.planning)
        ordered_names = ["entities", "issue_status"]

        _render_snapshot_tables(
            tables_by_name=tables_by_name,
            ordered_names=ordered_names,
            format_name=format_name,
            output_path=output,
            generated_at=core.planning.now().value.isoformat(),
        )

    except Exception as e:
        log.exception("status_error", error=str(e))
        RoadmapStatusPresenter.show_error(str(e))


def _render_snapshot_tables(
    tables_by_name: dict[str, "TableData"],
    ordered_names: list[str],
    format_name: str,
    output_path: Path | None,
    generated_at: str,
) -> None:
    normalized = format_name.lower()
    export_format = normalized if normalized != "rich" else "plain"

    if output_path:
        content = _format_snapshot_content(
            tables_by_name, ordered_names, export_format, generated_at
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        click.secho(f"✅ Saved to {output_path}", fg="green")
        return

    if normalized == "rich":
        manager = OutputManager(format="table")
        for index, name in enumerate(ordered_names):
            manager.render_table(tables_by_name[name])
            if index < len(ordered_names) - 1:
                click.echo()
        return

    content = _format_snapshot_content(
        tables_by_name, ordered_names, normalized, generated_at
    )
    click.echo(content)


def _format_snapshot_content(
    tables_by_name: dict[str, "TableData"],
    ordered_names: list[str],
    format_name: str,
    generated_at: str,
) -> str:
    if format_name == "json":
        payload = {
            "generated_at": generated_at,
            "tables": {name: tables_by_name[name].to_dict() for name in ordered_names},
        }
        return json.dumps(payload, indent=2, default=str)

    parts: list[str] = []
    for name in ordered_names:
        table = tables_by_name[name]
        formatter = OutputFormatter(table)

        if format_name == "plain":
            parts.append(formatter.to_plain_text())
        elif format_name == "csv":
            title = table.title or name
            parts.append(f"# {title}")
            parts.append(formatter.to_csv().rstrip())
        elif format_name == "markdown":
            parts.append(formatter.to_markdown())
        else:
            parts.append(formatter.to_plain_text())

    return "\n\n".join(part for part in parts if part)


def _build_snapshot_tables(planning) -> dict[str, TableData]:
    projects = planning.all_projects()
    milestones = planning.all_milestones()
    issues = planning.all_issues()
    visible_projects = tuple(
        item for item in projects if item.retention is RetentionState.VISIBLE
    )
    visible_milestones = tuple(
        item for item in milestones if item.retention is RetentionState.VISIBLE
    )
    visible_issues = tuple(
        item for item in issues if item.retention is RetentionState.VISIBLE
    )
    project_counts = Counter(item.status for item in visible_projects)
    milestone_counts = Counter(item.status for item in visible_milestones)
    issue_counts = Counter(item.status for item in visible_issues)
    archived_projects = sum(
        item.retention is RetentionState.ARCHIVED for item in projects
    )
    archived_milestones = sum(
        item.retention is RetentionState.ARCHIVED for item in milestones
    )
    archived_issues = sum(item.retention is RetentionState.ARCHIVED for item in issues)

    project_open = sum(
        project_counts[item]
        for item in (
            ProjectStatus.PLANNING,
            ProjectStatus.ACTIVE,
            ProjectStatus.ON_HOLD,
        )
    )
    project_closed = sum(
        project_counts[item]
        for item in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED)
    )
    milestone_open = milestone_counts[MilestoneStatus.OPEN]
    milestone_closed = milestone_counts[MilestoneStatus.CLOSED]
    issue_open = sum(
        issue_counts[item]
        for item in (
            IssueStatus.TODO,
            IssueStatus.IN_PROGRESS,
            IssueStatus.BLOCKED,
            IssueStatus.REVIEW,
        )
    )
    issue_closed = issue_counts[IssueStatus.CLOSED]
    entity_rows = [
        [
            "Projects",
            project_open,
            project_closed,
            archived_projects,
            len(projects),
        ],
        [
            "Milestones",
            milestone_open,
            milestone_closed,
            archived_milestones,
            len(milestones),
        ],
        ["Issues", issue_open, issue_closed, archived_issues, len(issues)],
    ]
    entity_rows.append(
        [
            "Total",
            project_open + milestone_open + issue_open,
            project_closed + milestone_closed + issue_closed,
            archived_projects + archived_milestones + archived_issues,
            len(projects) + len(milestones) + len(issues),
        ]
    )
    entities = TableData(
        columns=[
            ColumnDef("entity", "Entity", ColumnType.STRING, width=12),
            ColumnDef("open", "Open", ColumnType.INTEGER, width=6),
            ColumnDef("closed", "Closed", ColumnType.INTEGER, width=7),
            ColumnDef("archived", "Archived", ColumnType.INTEGER, width=9),
            ColumnDef("total", "Total", ColumnType.INTEGER, width=6),
        ],
        rows=entity_rows,
        title="Entities",
    )
    status_rows = [[item.value, issue_counts[item]] for item in IssueStatus]
    status_rows.append(["archived", archived_issues])
    status_rows.append(["Total", len(issues)])
    issue_status = TableData(
        columns=[
            ColumnDef("status", "Status", ColumnType.STRING, width=14),
            ColumnDef("count", "Count", ColumnType.INTEGER, width=7),
        ],
        rows=status_rows,
        title="Issue Status",
    )
    return {
        "entities": entities,
        "issue_status": issue_status,
    }


@click.command()
@verbose_option
@details_option
@format_option
@click.pass_context
def check_health(ctx: click.Context, verbose: bool, details: bool, format: str) -> None:
    """Check system health and component status.

    By default, shows a summary of health checks with status indicators.

    Use --details to see recommendations for fixes and ready-to-run commands.
    Use --format json to output machine-readable JSON with full details.
    Use --verbose to see all debug logs and detailed check information.
    """
    log = logger.bind(operation="health")
    log.info("starting_health_check", verbose=verbose, details=details, format=format)

    core = ctx.obj["core"]

    # Show header only for non-JSON formats
    if format.lower() != "json":
        presenter.present_health_header()

    try:
        # Run all health checks
        health_check = HealthCheck()
        checks = health_check.run_all_checks(core)

        # Format and display results
        formatter = HealthCheckFormatter(core)

        if format.lower() == "json":
            output = formatter.format_json(checks, details=details, hierarchical=True)
            click.echo(output)
        else:
            # Plain text format
            output = formatter.format_plain(checks, details=details)
            click.echo(output)

        # Log completion
        overall_status = HealthCheck.get_overall_status(checks)
        log.info("health_check_completed", status=overall_status)

    except Exception as e:
        log.exception("health_check_error", error=str(e))
        click.secho(f"❌ Health check failed: {e}", fg="red", bold=True)


@click.command()
@health_check_options
@click.option(
    "--fix-type",
    "-t",
    type=click.Choice(
        [
            "all",
            "old_backups",
            "duplicate_issues",
            "orphaned_issues",
            "folder_structure",
            "corrupted_comments",
            "data_integrity",
            "label_normalization",
            "milestone_name_normalization",
            "milestone_naming_compliance",
            "milestone_validation",
        ],
        case_sensitive=False,
    ),
    default="all",
    help="Which fix(es) to apply (default: all)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview changes without applying (default: disabled)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Auto-accept all suggestions without prompts",
)
@click.pass_context
def fix_health(
    ctx: click.Context,
    verbose: bool,
    details: bool,
    format: str,
    fix_type: str,
    dry_run: bool,
    yes: bool,
) -> None:
    """Apply automatic fixes for health issues.

    By default, applies safe fixes automatically. Use --dry-run to preview changes
    without applying them.

    Examples:
      roadmap health fix                        # Apply all safe fixes
      roadmap health fix --fix-type old_backups # Apply backup cleanup
      roadmap health fix --dry-run              # Preview all fixes
      roadmap health fix --fix-type old_backups --dry-run  # Preview backups
      roadmap health fix --yes                  # Apply all fixes without confirmation
    """
    log = logger.bind(operation="health_fix")
    log.info("starting_health_fix", fix_type=fix_type, dry_run=dry_run)

    core = ctx.obj["core"]

    try:
        orchestrator = HealthFixOrchestrator(core)

        # Get available fixers
        fixers = orchestrator.get_fixers()
        available_types = list(fixers.keys())

        # Determine which fixers to run
        if fix_type.lower() == "all":
            types_to_fix = available_types
        else:
            types_to_fix = [fix_type.lower()]

        # Validate fix types
        invalid_types = [t for t in types_to_fix if t not in available_types]
        if invalid_types:
            click.secho(f"❌ Unknown fix type(s): {', '.join(invalid_types)}", fg="red")
            click.echo(f"Available: {', '.join(available_types)}")
            return

        # Collect results
        results = []
        total_changes = 0

        for fix_t in types_to_fix:
            if dry_run:
                result = orchestrator.dry_run_fix(fix_t)
            else:
                result = orchestrator.apply_fix(fix_t, force=yes)

            if result:
                results.append(result)
                total_changes += result.changes_made

        # Display results
        if format.lower() == "json":
            output = _format_fix_results_json(results, dry_run)
            click.echo(output)
        else:
            _display_fix_results_plain(results, dry_run)

        log.info(
            "health_fix_completed",
            dry_run=dry_run,
            total_changes=total_changes,
            fixes_run=len(results),
        )

    except Exception as e:
        log.exception("health_fix_error", error=str(e))
        click.secho(f"❌ Health fix failed: {e}", fg="red", bold=True)


def _format_fix_results_json(results: list, dry_run: bool) -> str:
    """Format fix results as JSON.

    Args:
        results: List of FixResult objects
        dry_run: Whether this was a dry-run

    Returns:
        JSON string
    """
    total_changes = sum(r.changes_made for r in results)

    output = {
        "mode": "dry-run" if dry_run else "applied",
        "total_fixes": len(results),
        "total_changes": total_changes,
        "fixes": [r.to_dict() for r in results],
    }

    return json.dumps(output, indent=2, default=str)


def _display_fix_results_plain(results: list, dry_run: bool) -> None:
    """Display fix results in plain text format.

    Args:
        results: List of FixResult objects
        dry_run: Whether this was a dry-run
    """
    click.echo()
    if dry_run:
        click.secho("🔍 DRY-RUN PREVIEW (No changes made)", fg="cyan", bold=True)
    else:
        click.secho("✅ FIXES APPLIED", fg="green", bold=True)

    total_changes = 0
    for result in results:
        icon = "✅" if result.success else "❌"
        color = "green" if result.success else "red"

        click.secho(
            f"{icon} {result.fix_type}: {result.message}",
            fg=color,
        )

        if result.affected_items:
            for item in result.affected_items[:3]:  # Show first 3
                click.echo(f"   • {item}")
            if len(result.affected_items) > 3:
                click.echo(f"   ... and {len(result.affected_items) - 3} more")

        total_changes += result.changes_made

    click.echo()
    click.secho(
        f"Total changes: {total_changes}",
        fg="cyan",
    )

    if dry_run:
        click.echo("\n💡 To apply fixes, run without --dry-run:")
        click.echo("   roadmap health fix")


@click.group(invoke_without_command=True)
@details_option
@format_option
@verbose_option
@click.pass_context
@require_initialized
def health(ctx: click.Context, details: bool, format: str, verbose: bool) -> None:
    """Health and diagnostics commands.

    Provides infrastructure health checks and entity-level diagnostics.

    Examples:
      roadmap health              # Show health summary
      roadmap health --details    # Show recommendations and fix commands
      roadmap health --format json  # Output machine-readable JSON
      roadmap health scan         # Detailed entity-level scanning
    """
    if ctx.obj is None:
        ctx.obj = {}

    # Store options for subcommands
    ctx.ensure_object(dict)
    ctx.obj["details"] = details
    ctx.obj["format"] = format
    ctx.obj["verbose"] = verbose

    # If no subcommand was invoked, run health check with the provided options
    if ctx.invoked_subcommand is None:
        ctx.invoke(check_health, details=details, format=format, verbose=verbose)


# Register health subcommands (scan, fix, and check is now the default)
health.add_command(health_scan, name="scan")
health.add_command(fix_health, name="fix")
health.add_command(db_integrity, name="db-integrity")
