"""Versioned workspace diagnostics and bounded repair commands."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import (
    compatibility_warnings,
    require_initialized,
    verbose_message,
)
from roadmap.adapters.inbound.cli.planning_resolution import invoke
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
    if summary_only:
        payload["findings"] = []
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
        writer.writerows(payload["findings"])  # type: ignore[arg-type, ty:invalid-argument-type]
        return stream.getvalue()
    lines = [f"Roadmap health: {payload['status']}"]
    if summary_only:
        summary = payload["summary"]
        assert isinstance(summary, dict)
        lines.append(" ".join(f"{key}={summary[key]}" for key in summary))
    elif report.findings:
        for item in report.findings:
            lines.append(
                f"[{item.severity.value}] {item.finding_id} ({item.scope}): {item.message}"
            )
            if item.safe_action in {"projection", "recovery"}:
                lines.append(
                    f"  Preview repair: roadmap health fix --fix-type {item.safe_action} --dry-run"
                )
    else:
        lines.append("No findings.")
    return "\n".join(lines) + "\n"


def _filter_by_entity(findings: tuple, entities: tuple[str, ...]) -> tuple:
    if not entities:
        return findings
    selected = {value.casefold() for value in entities}
    return tuple(
        item for item in findings if item.scope.split("/", 1)[0].rstrip("s") in selected
    )


def _filter_by_severity(findings: tuple, severities: tuple[str, ...]) -> tuple:
    if not severities:
        return findings
    selected = {value.casefold() for value in severities}
    return tuple(item for item in findings if item.severity.value in selected)


def _filter_dependencies(findings: tuple, *, dependencies: bool) -> tuple:
    if dependencies:
        return findings
    return tuple(
        item for item in findings if item.finding_id != "canonical.broken-reference"
    )


def _filtered(
    report: HealthReport,
    entities: tuple[str, ...] = (),
    severities: tuple[str, ...] = (),
    *,
    dependencies: bool = True,
) -> HealthReport:
    findings = report.findings
    findings = _filter_by_entity(findings, entities)
    findings = _filter_by_severity(findings, severities)
    findings = _filter_dependencies(findings, dependencies=dependencies)
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
    compatibility_warnings(ctx)
    if ctx.info_name == "check":
        click.echo(
            "Deprecated through 0.3; removed in 0.4: health check; use health scan.",
            err=True,
        )
    del verbose, details
    report = invoke(lambda: ctx.obj["core"].health.scan())
    click.echo(_render(report, format_name), nl=False)
    if report.exit_code:
        raise click.exceptions.Exit(report.exit_code)


@click.command("scan")
@click.option(
    "--output",
    "-o",
    help="Destination file; legacy plain/json/csv tokens still mean format until 0.4",
)
@click.option(
    "--format",
    "-f",
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
@click.option("--with-dependencies/--no-dependencies", default=True)
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
    output: str | None,
    summary_only: bool,
    verbose: bool,
) -> None:
    """Scan canonical files, relationships, recovery state, and projection state."""
    compatibility_warnings(ctx)
    del details, group_by, verbose
    if output in {"plain", "json", "csv"}:
        if (
            ctx.get_parameter_source("format_name")
            is click.core.ParameterSource.COMMANDLINE
            and output != format_name
        ):
            raise click.UsageError("Legacy --output FORMAT conflicts with --format")
        click.echo(
            "Deprecated through 0.3; removed in 0.4: --output FORMAT; use --format. Use ./json (or ./csv, ./plain) for a destination with that name.",
            err=True,
        )
        format_name, output = output, None
    report = invoke(lambda: ctx.obj["core"].health.scan())
    report = _filtered(
        report,
        entities,
        severities,
        dependencies=with_dependencies,
    )
    content = _render(report, format_name, summary_only=summary_only)
    if output is None:
        click.echo(content, nl=False)
    else:
        try:
            with Path(output).open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
        except FileExistsError as error:
            raise click.ClickException(
                f"Refusing to overwrite existing report: {output}"
            ) from error
        except OSError as error:
            raise click.ClickException(
                f"Cannot write report {output}: {error}"
            ) from error
        click.echo(f"Exported health report to {output}", err=True)
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
    compatibility_warnings(ctx)
    click.echo(
        "Deprecated through 0.3; removed in 0.4: health db-integrity; use health scan.",
        err=True,
    )
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
    type=click.Choice(["projection", "recovery"]),
    required=True,
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
    compatibility_warnings(ctx)
    del details
    if repair_type not in {"projection", "recovery"}:
        raise click.UsageError(
            "Choose an explicit --fix-type projection or recovery; canonical edits and legacy shorthand are unsupported"
        )
    normalized = repair_type
    preview = invoke(lambda: ctx.obj["core"].health.repair(normalized, dry_run=True))
    verbose_message(
        verbose,
        f"Validated {len(preview.actions)} {repair_type} repair action(s); preview did not apply changes.",
    )
    if not dry_run and preview.actions and not confirmed:
        click.confirm("Apply the listed repair actions?", abort=True, default=False)
    result = (
        preview
        if dry_run
        else invoke(lambda: ctx.obj["core"].health.repair(normalized, dry_run=False))
    )
    if not dry_run:
        verbose_message(
            verbose,
            f"Completed {len(result.actions)} {repair_type} repair action(s); post-check exit code {result.report.exit_code}.",
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
    if ctx.invoked_subcommand is not None:
        for name in ("details", "format_name", "verbose"):
            if ctx.get_parameter_source(name) is click.core.ParameterSource.COMMANDLINE:
                raise click.UsageError(
                    "Health group options apply only to bare health; put options after the subcommand"
                )
    if ctx.invoked_subcommand is None:
        ctx.invoke(
            scan,
            details=details,
            format_name=format_name,
            verbose=verbose,
            entities=(),
            severities=(),
            group_by="entity",
            with_dependencies=True,
            summary_only=False,
            output=None,
        )


health.add_command(check_health)
health.add_command(scan)
health.add_command(fix_health)
health.add_command(db_integrity)
