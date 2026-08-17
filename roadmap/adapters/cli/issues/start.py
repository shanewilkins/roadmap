"""Start an issue through the target Application boundary."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
    timestamp,
)
from roadmap.common.datetime_parser import parse_user_datetime
from roadmap.common.logging import log_command


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
@log_command("issue_start", entity_type="issue", track_duration=True)
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
        from roadmap.core.services import IssueCreationService

        IssueCreationService(core).create_branch_for_issue(
            result.issue, branch_name, checkout, force
        )
