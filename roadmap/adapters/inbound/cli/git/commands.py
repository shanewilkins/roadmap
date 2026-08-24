"""Explicit local-only Git conveniences."""

from __future__ import annotations

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.issues.resolution import resolve_issue_id
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning


@click.group()
def git() -> None:
    """Inspect local Git state and manage explicit issue branch references."""


@git.command("status")
@click.pass_context
@require_initialized
def git_status(ctx: click.Context) -> None:
    """Show local repository state without reading remotes or credentials."""
    snapshot = invoke(lambda: ctx.obj["core"].local_git.inspect())
    if not snapshot.is_repository:
        click.echo("Not a Git repository.")
        return
    click.echo(f"Branch: {snapshot.branch or '(detached or unborn HEAD)'}")
    click.echo(f"HEAD: {snapshot.head[:12] if snapshot.head else '(no commits)'}")
    click.echo(f"Changed paths: {len(snapshot.changed_paths)}")
    for path in snapshot.changed_paths:
        click.echo(f"- {path}")
    if snapshot.linked_issue_ids:
        click.echo("Linked issues: " + ", ".join(map(str, snapshot.linked_issue_ids)))
    else:
        click.echo("Linked issues: none")


@git.command("branch")
@click.argument("issue_id")
@click.option("--checkout/--no-checkout", default=True, show_default=True)
@click.pass_context
@require_initialized
def git_branch(ctx: click.Context, issue_id: str, checkout: bool) -> None:
    """Create and link a safe local branch for one canonical issue."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    result = invoke(
        lambda: core.local_git.create_issue_branch(identity, checkout=checkout)
    )
    if result.dirty_paths:
        click.echo(
            f"Warning: branch was created with {len(result.dirty_paths)} changed path(s) in the worktree.",
            err=True,
        )
    action = "Created and checked out" if checkout else "Created"
    click.echo(f"{action} branch: {result.branch}")
    click.echo(f"Linked issue: {result.issue_id}")
    projection_warning(result)


@git.command("link")
@click.argument("issue_id")
@click.pass_context
@require_initialized
def git_link(ctx: click.Context, issue_id: str) -> None:
    """Link one issue to the current local branch."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    result = invoke(lambda: core.local_git.link_current_branch(identity))
    click.echo(f"Linked issue {result.issue_id} to branch: {result.branch}")
    projection_warning(result)
