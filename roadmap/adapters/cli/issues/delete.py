"""Delete issue command."""

import click

from roadmap.adapters.cli.crud import BaseDelete, EntityType
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.infrastructure.logging import log_command


class IssueDelete(BaseDelete):
    """Delete issue command implementation."""

    entity_type = EntityType.ISSUE


@click.command("delete")
@click.argument("issue_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@log_command("issue_delete", entity_type="issue", track_duration=True)
@require_initialized
def delete_issue(
    ctx: click.Context,
    issue_id: str,
    yes: bool,
):
    """Delete an issue."""
    core = ctx.obj["core"]
    deleter = IssueDelete(core)

    deleter.execute(entity_id=issue_id, force=yes)
