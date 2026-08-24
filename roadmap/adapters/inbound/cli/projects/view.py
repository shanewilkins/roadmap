"""View canonical project details and derived progress."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import invoke


@click.command("view")
@click.argument("project_id")
@click.pass_context
@require_initialized
def view_project(ctx, project_id: str) -> None:
    """Display a project and Application-derived planning totals."""
    summary = invoke(lambda: ctx.obj["core"].planning.project(project_id))
    project = summary.project
    click.echo(f"Project: {project.name}")
    click.echo(f"ID: {project.id}")
    click.echo(f"Status: {project.status.value}")
    click.echo(f"Priority: {project.priority.value}")
    click.echo(f"Owner: {project.owner or 'Unassigned'}")
    click.echo(f"Progress: {summary.progress:.1f}%")
    click.echo(f"Milestones: {summary.milestone_count}")
    click.echo(f"Issues: {summary.closed_count}/{summary.issue_count} closed")
    click.echo(f"Estimate: {summary.estimated_hours:.1f}h")
    if project.repository_url:
        click.echo(f"Repository: {project.repository_url}")
    if project.content:
        click.echo("\n" + project.content)
