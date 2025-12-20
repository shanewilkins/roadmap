"""Health scan command for comprehensive entity-level diagnostics.

Provides detailed scanning of issues, milestones, and projects with:
- Output format selection (plain, json, csv)
- Entity type filtering
- Severity filtering
- Dependency analysis
- Exit codes for CI/CD integration (0=healthy, 1=degraded, 2=unhealthy)
"""

import sys

import click
from structlog import get_logger

from roadmap.adapters.cli.health.formatters import get_formatter
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.core.services.dependency_analyzer import DependencyAnalyzer
from roadmap.core.services.entity_health_scanner import (
    EntityHealthScanner,
)

logger = get_logger()


@click.command()
@click.option(
    "--output",
    "-o",
    type=click.Choice(["plain", "json", "csv"], case_sensitive=False),
    default="plain",
    help="Output format (default: plain)",
)
@click.option(
    "--filter-entity",
    "-e",
    multiple=True,
    type=click.Choice(["issue", "milestone", "project"], case_sensitive=False),
    help="Filter by entity type (can specify multiple times)",
)
@click.option(
    "--filter-severity",
    "-s",
    multiple=True,
    type=click.Choice(["info", "warning", "error", "critical"], case_sensitive=False),
    help="Filter by severity level (can specify multiple times)",
)
@click.option(
    "--group-by",
    "-g",
    type=click.Choice(["entity", "severity", "type"], case_sensitive=False),
    default="entity",
    help="Grouping strategy (default: entity)",
)
@click.option(
    "--with-dependencies",
    is_flag=True,
    default=True,
    help="Include dependency analysis (default: enabled)",
)
@click.option(
    "--no-dependencies",
    is_flag=True,
    help="Skip dependency analysis",
)
@click.option(
    "--summary-only",
    is_flag=True,
    help="Show only summary, not detailed results",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show verbose output",
)
@click.pass_context
@require_initialized
def scan(
    ctx: click.Context,
    output: str,
    filter_entity: tuple[str],
    filter_severity: tuple[str],
    group_by: str,
    with_dependencies: bool,
    no_dependencies: bool,
    summary_only: bool,
    verbose: bool,
) -> None:
    """Scan roadmap for entity-level health issues.

    Performs detailed diagnostics on all issues, milestones, and projects
    including validation of content, dates, estimates, dependencies, and more.

    Exit codes:
      0 = All entities healthy
      1 = Some entities degraded (warnings present)
      2 = Unhealthy entities found (errors present)
    """
    log = logger.bind(operation="health_scan")

    try:
        core = ctx.obj["core"]

        # Determine if we should scan dependencies
        scan_deps = with_dependencies and not no_dependencies

        # Get formatter
        formatter = get_formatter(output)

        # Scan entities
        scanner = EntityHealthScanner(core)
        entity_reports = scanner.scan_all()
        log.info("entities_scanned", count=len(entity_reports))

        # Apply entity type filter
        if filter_entity:
            entity_filter = {f.lower() for f in filter_entity}
            entity_reports = [
                r for r in entity_reports if r.entity_type.value in entity_filter
            ]
            log.info("entity_filter_applied", remaining=len(entity_reports))

        # Apply severity filter
        if filter_severity:
            severity_filter = {f.lower() for f in filter_severity}
            entity_reports = [
                r
                for r in entity_reports
                if any(issue.severity.value in severity_filter for issue in r.issues)
            ]
            log.info("severity_filter_applied", remaining=len(entity_reports))

        # Group reports if requested
        if group_by.lower() != "entity":
            entity_reports = _apply_grouping(entity_reports, group_by)

        # Scan dependencies if requested
        dependency_analysis = None
        if scan_deps:
            try:
                analyzer = DependencyAnalyzer()
                all_issues = core.issue_repository.list()
                dependency_analysis = analyzer.analyze(all_issues)
                log.info(
                    "dependencies_analyzed",
                    total_issues=dependency_analysis.total_issues,
                    problems=len(dependency_analysis.problems),
                )
            except Exception as e:
                log.warning("dependency_analysis_failed", error=str(e))
                dependency_analysis = None

        # Determine overall health status
        exit_code = _determine_exit_code(entity_reports, dependency_analysis)

        # Format and output results
        if summary_only:
            output_text = formatter.format_summary(entity_reports, dependency_analysis)
        else:
            output_text = formatter.format_entity_reports(entity_reports)
            if scan_deps and dependency_analysis:
                output_text += "\n" + formatter.format_dependency_analysis(
                    dependency_analysis
                )
            output_text += "\n" + formatter.format_summary(
                entity_reports, dependency_analysis
            )

        click.echo(output_text)

        # Log summary if verbose
        if verbose:
            _log_summary(entity_reports, dependency_analysis, log)

        sys.exit(exit_code)

    except Exception as e:
        log.exception("scan_failed", error=str(e))
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(2)


def _determine_exit_code(entity_reports: list, dependency_analysis=None) -> int:
    """Determine exit code based on health status.

    Exit codes:
      0 = All healthy (no errors, no degradation)
      1 = Degraded (warnings present but no errors)
      2 = Unhealthy (errors present)
    """
    # Check entity health
    unhealthy = sum(1 for r in entity_reports if not r.is_healthy)
    degraded = sum(1 for r in entity_reports if r.is_degraded and r.is_healthy)

    if unhealthy > 0:
        return 2

    # Check dependency health
    if dependency_analysis:
        if not dependency_analysis.is_healthy:
            return 2
        if dependency_analysis.warning_count > 0:
            return 1

    if degraded > 0:
        return 1

    return 0


def _apply_grouping(reports: list, group_by: str) -> list:
    """Apply grouping strategy to reports.

    This is a placeholder - actual implementation would reorganize the reports.
    For now, returns reports as-is.
    """
    # Could group by:
    # - severity: combine all errors together, all warnings, etc.
    # - type: all issue health issues together, all milestone issues, etc.
    # - entity: default, keep as-is
    return reports


def _log_summary(entity_reports: list, dependency_analysis, log):
    """Log summary information if verbose."""
    total_entities = len(entity_reports)
    healthy = sum(1 for r in entity_reports if r.is_healthy)
    degraded = sum(1 for r in entity_reports if r.is_degraded)
    unhealthy = total_entities - healthy - degraded

    error_count = sum(r.error_count for r in entity_reports)
    warning_count = sum(r.warning_count for r in entity_reports)
    info_count = sum(r.info_count for r in entity_reports)

    log.info(
        "health_summary",
        total_entities=total_entities,
        healthy=healthy,
        degraded=degraded,
        unhealthy=unhealthy,
        total_issues=error_count + warning_count + info_count,
        errors=error_count,
        warnings=warning_count,
        info=info_count,
    )

    if dependency_analysis:
        log.info(
            "dependency_summary",
            total_issues=dependency_analysis.total_issues,
            with_dependencies=dependency_analysis.issues_with_dependencies,
            with_problems=dependency_analysis.issues_with_problems,
            circular_chains=len(dependency_analysis.circular_chains),
        )
