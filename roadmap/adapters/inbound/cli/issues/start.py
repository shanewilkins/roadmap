"""Start an issue through the target Application boundary."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.datetime_parser import parse_user_datetime
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
    timestamp,
)


def _start_time(value: str | None):
    if value is None:
        return None
    parsed = parse_user_datetime(value, "UTC")
    if parsed is None:
        raise click.ClickException(
            "Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"
        )
    return timestamp(parsed)


@click.command("start")
@click.argument("issue_id")
@click.option("--date", help="Start date (YYYY-MM-DD HH:MM, defaults to now)")
@click.option("--git-branch/--no-git-branch", default=False)
@click.option("--checkout/--no-checkout", default=True)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option("--force", is_flag=True, help="Allow branch creation with changes")
@click.pass_context
@require_initialized
def start_issue(
    ctx: click.Context,
    issue_id: str,
    date: str | None,
    git_branch: bool,
    checkout: bool,
    branch_name: str | None,
    force: bool,
) -> None:
    """Start work and record the issue's actual start time."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    result = invoke(lambda: core.issue_mutations.start(identity, _start_time(date)))
    click.echo(f"Started issue {identity}")
    projection_warning(result)
    if git_branch:
        branch = invoke(
            lambda: core.local_git.create_issue_branch(
                result.issue.id,
                checkout=checkout,
                branch_name=branch_name,
                force=force,
            )
        )
        click.echo(f"Created branch: {branch.branch}")
