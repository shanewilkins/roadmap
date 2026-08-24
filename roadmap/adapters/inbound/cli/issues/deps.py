"""Manage reciprocal issue dependencies through Application use cases."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)


@click.group("deps")
def deps() -> None:
    """Manage issue dependencies."""


def _ids(ctx: click.Context, issue_id: str, dependency_id: str):
    core = ctx.obj["core"]
    return core, resolve_issue_id(core, issue_id), resolve_issue_id(core, dependency_id)


@deps.command("add")
@click.argument("issue_id")
@click.argument("dependency_id")
@click.pass_context
@require_initialized
def add_dependency(ctx: click.Context, issue_id: str, dependency_id: str) -> None:
    """Make ISSUE_ID depend on DEPENDENCY_ID."""
    core, identity, dependency = _ids(ctx, issue_id, dependency_id)
    result = invoke(lambda: core.issue_mutations.add_dependency(identity, dependency))
    click.echo(f"Added dependency: {identity} depends on {dependency}")
    projection_warning(result)


@deps.command("remove")
@click.argument("issue_id")
@click.argument("dependency_id")
@click.pass_context
@require_initialized
def remove_dependency(ctx: click.Context, issue_id: str, dependency_id: str) -> None:
    """Remove DEPENDENCY_ID from ISSUE_ID."""
    core, identity, dependency = _ids(ctx, issue_id, dependency_id)
    result = invoke(
        lambda: core.issue_mutations.remove_dependency(identity, dependency)
    )
    click.echo(f"Removed dependency: {identity} no longer depends on {dependency}")
    projection_warning(result)


@deps.command("update")
@click.argument("issue_id")
@click.argument("old_dependency_id")
@click.argument("new_dependency_id")
@click.pass_context
@require_initialized
def update_dependency(
    ctx: click.Context,
    issue_id: str,
    old_dependency_id: str,
    new_dependency_id: str,
) -> None:
    """Replace OLD_DEPENDENCY_ID with NEW_DEPENDENCY_ID on ISSUE_ID."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    old = resolve_issue_id(core, old_dependency_id)
    new = resolve_issue_id(core, new_dependency_id)
    result = invoke(lambda: core.issue_mutations.replace_dependency(identity, old, new))
    click.echo(f"Updated dependency: {old} -> {new}")
    projection_warning(result)
