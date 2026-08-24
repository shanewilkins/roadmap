"""Versioned workspace diagnostics and bounded repair commands."""

from __future__ import annotations

import csv
import io
import json

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import invoke
from roadmap.application.contracts import HealthReport, RepairResult


def _payload(report: HealthReport) -> dict[str, object]:
    counts = dict.fromkeys(("info", "warning", "error", "critical"), 0)
    for finding in report.findings:
        counts[finding.severity.value] += 1
    return {
        "schema_version": 1,
        "kind": "roadmap.health",
        "status": (
            "unhealthy"
            if report.exit_code == 2
            else "degraded"
            if report.exit_code == 1
            else "healthy"
        ),
        "exit_code": report.exit_code,
        "summary": counts,
        "findings": [
            {
                "finding_id": item.finding_id,
                "severity": item.severity.value,
                "scope": item.scope,
                "entity_id": item.entity_id,
                "message": item.message,
                "safe_action": item.safe_action,
            }
            for item in report.findings
        ],
    }


def _render(
    report: HealthReport, format_name: str, *, summary_only: bool = False
) -> str:
    payload = _payload(report)
    if format_name == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if format_name == "csv":
        stream = io.StringIO(newline="")
        fields = (
            "finding_id",
            "severity",
            "scope",
            "entity_id",
            "message",
            "safe_action",
        )
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        if not summary_only:
            writer.writerows(payload["findings"])  # type: ignore[arg-type]
        return stream.getvalue()
    lines = [f"Roadmap health: {payload['status']}"]
    if summary_only:
        summary = payload["summary"]
        assert isinstance(summary, dict)
        lines.append(" ".join(f"{key}={summary[key]}" for key in summary))
    elif report.findings:
        lines.extend(
            f"[{item.severity.value}] {item.finding_id} ({item.scope}): {item.message}"
            for item in report.findings
        )
    else:
        lines.append("No findings.")
    return "\n".join(lines) + "\n"


def _filtered(
    report: HealthReport,
    entities: tuple[str, ...] = (),
    severities: tuple[str, ...] = (),
    *,
    dependencies: bool = True,
) -> HealthReport:
    findings = report.findings
    if entities:
        selected = {value.casefold() for value in entities}
        findings = tuple(
            item
            for item in findings
            if item.scope.split("/", 1)[0].rstrip("s") in selected
        )
    if severities:
        selected = {value.casefold() for value in severities}
        findings = tuple(item for item in findings if item.severity.value in selected)
    if not dependencies:
        findings = tuple(
            item for item in findings if item.finding_id != "canonical.broken-reference"
        )
    return HealthReport(findings)


@click.command("check", hidden=True)
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.option("--details", is_flag=True)
@click.option(
    "--format",
    "-f",
    "format_name",
    type=click.Choice(["plain", "json"]),
    default="plain",
)
@click.pass_context
def check_health(
    ctx: click.Context, verbose: bool, details: bool, format_name: str
) -> None:
    """Run the default read-only health scan."""
    del verbose, details
    report = invoke(lambda: ctx.obj["core"].health.scan())
    click.echo(_render(report, format_name), nl=False)
    if report.exit_code:
        raise click.exceptions.Exit(report.exit_code)


@click.command("scan")
@click.option(
    "--output",
    "-o",
    "format_name",
    type=click.Choice(["plain", "json", "csv"]),
    default="plain",
)
@click.option("--details", is_flag=True)
@click.option(
    "--filter-entity",
    "-e",
    "entities",
    multiple=True,
    type=click.Choice(["issue", "milestone", "project"]),
)
@click.option(
    "--filter-severity",
    "-s",
    "severities",
    multiple=True,
    type=click.Choice(["info", "warning", "error", "critical"]),
)
@click.option(
    "--group-by",
    "-g",
    type=click.Choice(["entity", "severity", "type"]),
    default="entity",
)
@click.option("--with-dependencies", is_flag=True, default=True)
@click.option("--no-dependencies", is_flag=True)
@click.option("--summary-only", is_flag=True)
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.pass_context
def scan(
    ctx: click.Context,
    format_name: str,
    details: bool,
    entities: tuple[str, ...],
    severities: tuple[str, ...],
    group_by: str,
    with_dependencies: bool,
    no_dependencies: bool,
    summary_only: bool,
    verbose: bool,
) -> None:
    """Scan canonical files, relationships, recovery state, and projection state."""
    del details, group_by, verbose
    report = invoke(lambda: ctx.obj["core"].health.scan())
    report = _filtered(
        report,
        entities,
        severities,
        dependencies=with_dependencies and not no_dependencies,
    )
    click.echo(_render(report, format_name, summary_only=summary_only), nl=False)
    if report.exit_code:
        raise click.exceptions.Exit(report.exit_code)


@click.command("db-integrity")
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.option("--details", is_flag=True)
@click.option(
    "--format",
    "-f",
    "format_name",
    type=click.Choice(["plain", "json"]),
    default="plain",
)
@click.option("--show-ids", is_flag=True)
@click.option("--json", "json_output", is_flag=True)
@click.option("--limit", type=int, default=20, show_default=True)
@click.pass_context
def db_integrity(
    ctx: click.Context,
    verbose: bool,
    details: bool,
    format_name: str,
    show_ids: bool,
    json_output: bool,
    limit: int,
) -> None:
    """Inspect canonical documents against the rebuildable projection."""
    del verbose, details, show_ids, limit
    report = invoke(lambda: ctx.obj["core"].health.scan())
    selected = HealthReport(
        tuple(
            item
            for item in report.findings
            if item.finding_id.startswith(("canonical.", "projection."))
        )
    )
    click.echo(_render(selected, "json" if json_output else format_name), nl=False)
    if selected.exit_code:
        raise click.exceptions.Exit(selected.exit_code)


_LEGACY_FIX_TYPES = [
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
    "projection",
    "recovery",
]


@click.command("fix")
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.option("--details", is_flag=True)
@click.option(
    "--format",
    "-f",
    "format_name",
    type=click.Choice(["plain", "json"]),
    default="plain",
)
@click.option(
    "--fix-type",
    "repair_type",
    "-t",
    type=click.Choice(_LEGACY_FIX_TYPES),
    default="all",
)
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "confirmed", "-y", is_flag=True)
@click.pass_context
def fix_health(
    ctx: click.Context,
    verbose: bool,
    details: bool,
    format_name: str,
    repair_type: str,
    dry_run: bool,
    confirmed: bool,
) -> None:
    """Preview or apply recovery and projection rebuild actions."""
    del verbose, details
    normalized = "data_integrity" if repair_type == "all" else repair_type
    preview = invoke(lambda: ctx.obj["core"].health.repair(normalized, dry_run=True))
    if not dry_run and preview.actions and not confirmed:
        click.confirm("Apply the listed repair actions?", abort=True, default=False)
    result = (
        preview
        if dry_run
        else invoke(lambda: ctx.obj["core"].health.repair(normalized, dry_run=False))
    )
    click.echo(_render_repair(result, format_name), nl=False)
    if result.report.exit_code:
        raise click.exceptions.Exit(result.report.exit_code)


def _render_repair(result: RepairResult, format_name: str) -> str:
    if format_name == "json":
        return (
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "roadmap.health-repair",
                    "mode": "dry-run" if result.dry_run else "applied",
                    "actions": [
                        {
                            "action_id": action.action_id,
                            "description": action.description,
                            "targets": list(action.targets),
                        }
                        for action in result.actions
                    ],
                    "post_check": _payload(result.report),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    heading = "Repair preview" if result.dry_run else "Repair applied"
    lines = [heading]
    lines.extend(
        f"- {action.action_id}: {action.description}" for action in result.actions
    )
    if not result.actions:
        lines.append("No applicable repair actions.")
    lines.append(f"Post-check exit code: {result.report.exit_code}")
    return "\n".join(lines) + "\n"


@click.group(invoke_without_command=True)
@click.option("--details", is_flag=True)
@click.option(
    "--format",
    "-f",
    "format_name",
    type=click.Choice(["plain", "json"]),
    default="plain",
)
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
def health(ctx: click.Context, details: bool, format_name: str, verbose: bool) -> None:
    """Read-only diagnostics with explicit, previewable repair."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(
            check_health, details=details, format_name=format_name, verbose=verbose
        )


health.add_command(scan)
health.add_command(fix_health)
health.add_command(db_integrity)
