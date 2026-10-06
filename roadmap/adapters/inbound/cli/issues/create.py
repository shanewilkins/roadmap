"""Create an issue through the target Application boundary."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_ids,
)
from roadmap.adapters.inbound.cli.planning_resolution import resolve_milestone_id
from roadmap.application.contracts import IssueCreateCommand
from roadmap.domain.types import IssueType, Priority, Title


def _report_created(result, assignee: str | None, print_id: bool) -> None:
    if print_id:
        click.echo(str(result.issue.id))
    else:
        click.echo(f"Created issue: [{result.issue.id}] {result.issue.title}")
    if not print_id and assignee is None and result.issue.assignee:
        click.echo(f"Auto-detected assignee from Git: {result.issue.assignee}")
        click.echo(f"Assignee: {result.issue.assignee}")
    if print_id and result.projection_stale:
        click.echo(
            "Warning: SQLite projection is stale; canonical Markdown was saved.",
            err=True,
        )
    elif not print_id:
        projection_warning(result)


@click.command("create")
@click.option(
    "--print-id", is_flag=True, help="Print only the created issue ID to stdout."
)
@click.option("--title", required=True, help="Issue title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
)
@click.option(
    "--type",
    "-t",
    "issue_type",
    type=click.Choice(["feature", "bug", "other"]),
    default="other",
)
@click.option("--milestone", "-m", help="Assign to milestone")
@click.option("--assignee", "-a", help="Assign to team member")
@click.option("--labels", "-l", multiple=True, help="Add labels")
@click.option("--estimate", "-e", type=float, help="Estimated hours")
@click.option("--depends-on", multiple=True, help="Issue IDs this depends on")
@click.option("--blocks", multiple=True, help="Issue IDs this blocks")
@click.option("--content", "-d", help="Markdown description")
@click.option("--git-branch", is_flag=True, help="Create a Git branch")
@click.option("--checkout/--no-checkout", default=True)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option("--force", is_flag=True, help="Allow branch creation with changes")
@click.pass_context
@require_initialized
def create_issue(
    ctx: click.Context,
    title: str,
    priority: str,
    issue_type: str,
    milestone: str | None,
    assignee: str | None,
    labels: tuple[str, ...],
    estimate: float | None,
    depends_on: tuple[str, ...],
    blocks: tuple[str, ...],
    content: str | None,
    git_branch: bool,
    checkout: bool,
    branch_name: str | None,
    force: bool,
    print_id: bool,
) -> None:
    """Create a new canonical issue."""
    core = ctx.obj["core"]
    command = invoke(
        lambda: IssueCreateCommand(
            title=Title(title),
            priority=Priority(priority),
            issue_type=IssueType(issue_type),
            milestone_id=resolve_milestone_id(core, milestone) if milestone else None,
            assignee=assignee,
            labels=labels,
            estimated_hours=estimate,
            depends_on=resolve_issue_ids(core, depends_on),
            blocks=resolve_issue_ids(core, blocks),
            content=content or "",
        )
    )
    result = invoke(lambda: core.issue_mutations.create(command))
    _report_created(result, assignee, print_id)
    if git_branch:
        branch = invoke(
            lambda: core.local_git.create_issue_branch(
                result.issue.id,
                checkout=checkout,
                branch_name=branch_name,
                force=force,
            )
        )
        click.echo(f"Created branch: {branch.branch}", err=print_id)
