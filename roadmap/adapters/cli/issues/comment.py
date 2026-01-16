"""Comment management commands for issues."""

import click

from roadmap.adapters.cli.cli_command_helpers import (
    ensure_entity_exists,
    require_initialized,
)
from roadmap.common.console import get_console
from roadmap.common.logging import log_command, verbose_output
from roadmap.core.services.comment.comment_service import CommentService


@click.group("comment")
def comment_group():
    """Manage comments on issues."""
    pass


@click.command("add")
@click.argument("issue_id")
@click.argument("body")
@click.option(
    "--author",
    "-a",
    default=None,
    help="Author of comment (defaults to current user)",
)
@click.option(
    "--reply-to",
    "-r",
    type=int,
    default=None,
    help="Comment ID this is a reply to",
)
@click.pass_context
@require_initialized
@verbose_output
@log_command("issue_comment_add", entity_type="comment", track_duration=True)
def add_comment(
    ctx: click.Context,
    issue_id: str,
    body: str,
    author: str | None,
    reply_to: int | None,
):
    """Add a comment to an issue.

    BODY: Comment text (markdown supported)

    Example:
        roadmap issue comment add abc123 "Great work! This looks good."
        roadmap issue comment add abc123 "I disagree" --reply-to 12345
    """
    core = ctx.obj["core"]
    console = get_console()

    # Ensure issue exists
    issue = ensure_entity_exists(core, "issue", issue_id)

    # Resolve author (use provided or default to system user)
    if not author:
        import getpass

        author = getpass.getuser()

    # Validate comment body
    if not body or not body.strip():
        console.print("❌ Comment body cannot be empty", style="red")
        return

    # Create the comment
    try:
        comment = CommentService.create_comment(
            author=author,
            body=body,
            entity_id=issue.id,
            in_reply_to=reply_to,
        )
    except Exception as e:
        console.print(f"❌ Failed to create comment: {e}", style="red")
        return

    # If replying to a comment, validate that comment exists
    if reply_to is not None:
        if not any(c.id == reply_to for c in issue.comments):
            console.print(
                f"❌ Cannot find comment {reply_to} to reply to",
                style="red",
            )
            return

    # Add comment to issue
    issue.comments.append(comment)

    # Update the issue
    try:
        core.issues.update(issue.id, {"comments": issue.comments})
        console.print(
            f"✅ Comment added to issue {issue.id}",
            style="green",
        )
        console.print(f"   By: {comment.author}")
        console.print(f"   ID: {comment.id}")
        if reply_to:
            console.print(f"   Replying to: {reply_to}")
    except Exception as e:
        console.print(f"❌ Failed to update issue: {e}", style="red")


@click.command("list")
@click.argument("issue_id")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
@require_initialized
def list_comments(ctx: click.Context, issue_id: str, format: str):
    """List comments on an issue.

    Example:
        roadmap issue comment list abc123
        roadmap issue comment list abc123 --format json
    """
    core = ctx.obj["core"]
    console = get_console()

    # Ensure issue exists
    issue = ensure_entity_exists(core, "issue", issue_id)

    if not issue.comments:
        console.print("[dim]No comments yet[/dim]")
        return

    if format == "json":
        # Convert comments to JSON-serializable format
        comments_data = []
        for comment in issue.comments:
            comments_data.append(
                {
                    "id": comment.id,
                    "author": comment.author,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat(),
                    "in_reply_to": comment.in_reply_to,
                }
            )
        console.print_json(data=comments_data)
    else:
        # Text format - show comments in thread view
        threads = CommentService.build_comment_threads(issue.comments)

        # Show top-level comments and their replies
        top_level_ids = [k for k in threads.keys() if k is not None]
        for top_level_id in sorted(top_level_ids):
            for comment in threads.get(top_level_id, []):
                console.print(
                    CommentService.format_comment_for_display(comment, indent=0)
                )

                # Show replies to this comment
                if comment.id in threads:
                    for reply in threads[comment.id]:
                        console.print(
                            CommentService.format_comment_for_display(reply, indent=1)
                        )

                console.print()  # Blank line between threads


# Register commands with group
comment_group.add_command(add_comment, name="add")
comment_group.add_command(list_comments, name="list")
