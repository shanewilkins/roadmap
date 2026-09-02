"""Explicit workspace schema migration command."""

import json
from dataclasses import asdict

import click

from roadmap.application.failures import ApplicationFailure


def _payload(plan) -> dict:
    payload = asdict(plan)
    payload["required"] = plan.required
    return payload


def _plain_plan(plan, dry_run: bool) -> None:
    heading = "Migration dry run" if dry_run else "Migration preflight"
    click.echo(
        f"{heading}: workspace schema {plan.source_version} -> {plan.target_version}"
    )
    for item in plan.changes:
        source = f"{item.source} -> " if item.source else ""
        click.echo(f"  {item.operation}: {source}{item.target}")
    for warning in plan.warnings:
        click.echo(f"Warning: {warning}", err=True)
    if plan.conflicts:
        click.echo("Conflicts:", err=True)
        for conflict in plan.conflicts:
            click.echo(f"  - {conflict}", err=True)
        return
    if not plan.required:
        click.echo("Workspace is already current; no changes are required.")


def _report_preflight(plan, dry_run: bool, output_format: str) -> None:
    if output_format == "json" and (dry_run or plan.conflicts or not plan.required):
        click.echo(json.dumps(_payload(plan), indent=2, sort_keys=True))
    elif output_format == "plain":
        _plain_plan(plan, dry_run)
    if plan.conflicts:
        raise click.ClickException(
            "Migration preflight found conflicts; no files changed."
        )


def _report_result(plan, result, output_format: str) -> None:
    if output_format == "json":
        output = _payload(plan)
        output.update(
            {
                "status": "migrated",
                "changed": result.changed,
                "projection_rebuilt": result.projection_rebuilt,
            }
        )
        click.echo(json.dumps(output, indent=2, sort_keys=True))
    else:
        click.echo(
            f"Migrated workspace to schema {result.target_version}; "
            f"{result.changed} planned changes applied."
        )
        click.echo("SQLite projection rebuilt from canonical documents.")


@click.command("migrate")
@click.option(
    "--dry-run", is_flag=True, help="Enumerate and validate changes without writing."
)
@click.option("--yes", "-y", is_flag=True, help="Apply without confirmation.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["plain", "json"], case_sensitive=False),
    default="plain",
    show_default=True,
)
@click.pass_context
def migrate(ctx: click.Context, dry_run: bool, yes: bool, output_format: str) -> None:
    """Upgrade an existing 0.1.1 workspace to the 0.2 canonical layout."""
    migration = ctx.obj["migration_factory"]()
    try:
        plan = migration.preflight()
        _report_preflight(plan, dry_run, output_format)
        if dry_run or not plan.required:
            return
        if not yes:
            click.confirm("Apply this canonical workspace migration?", abort=True)
        result = migration.execute(plan.fingerprint)
    except ApplicationFailure as error:
        raise click.ClickException(str(error)) from error

    _report_result(plan, result, output_format)
