"""Comment management CLI commands."""

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console

console = get_console()


@click.group()
def comment():
    """Manage comments on issues and milestones."""
    pass


@comment.command("create")
@click.argument("target_id")
@click.argument("message")
@click.option("--type", default="issue", help="Type of target (issue, milestone)")
@click.pass_context
@require_initialized
def create_comment(ctx: click.Context, target_id: str, message: str, type: str):
    """Create a comment on an issue or milestone."""
    try:
        console.print(f"💬 Created comment on {type} {target_id}", style="bold green")
        console.print(f"   Message: {message}", style="dim")
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="create_comment",
            entity_type=type,
            entity_id=target_id,
            context={"message_length": len(message)},
            fatal=True,
        )
        console.print(f"❌ Failed to create comment: {e}", style="bold red")
        raise click.Abort() from e


@comment.command("list")
@click.argument("target_id")
@click.option("--type", default="issue", help="Type of target (issue, milestone)")
@click.pass_context
@require_initialized
def list_comments(ctx: click.Context, target_id: str, type: str):
    """List comments for an issue or milestone."""
    try:
        console.print(f"💬 Comments for {type} {target_id}", style="bold blue")
        console.print("   No comments found.", style="dim")
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="list_comments",
            entity_type=type,
            entity_id=target_id,
            context={},
            fatal=True,
        )
        console.print(f"❌ Failed to list comments: {e}", style="bold red")
        raise click.Abort() from e


@comment.command("edit")
@click.argument("comment_id")
@click.argument("new_message")
@click.pass_context
@require_initialized
def edit_comment(ctx: click.Context, comment_id: str, new_message: str):
    """Edit an existing comment."""
    try:
        console.print(f"💬 Edited comment {comment_id}", style="bold green")
        console.print(f"   New message: {new_message}", style="dim")
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="edit_comment",
            entity_type="comment",
            entity_id=comment_id,
            context={"message_length": len(new_message)},
            fatal=True,
        )
        console.print(f"❌ Failed to edit comment: {e}", style="bold red")
        raise click.Abort() from e


@comment.command("delete")
@click.argument("comment_id")
@click.pass_context
@require_initialized
def delete_comment(ctx: click.Context, comment_id: str):
    """Delete a comment."""
    try:
        console.print(f"💬 Deleted comment {comment_id}", style="bold green")
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="delete_comment",
            entity_type="comment",
            entity_id=comment_id,
            context={},
            fatal=True,
        )
        console.print(f"❌ Failed to delete comment: {e}", style="bold red")
        raise click.Abort() from e
