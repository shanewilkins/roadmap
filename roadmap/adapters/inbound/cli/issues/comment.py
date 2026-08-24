"""Issue comment commands backed by canonical issue documents."""

import getpass
import json

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command, verbose_output
from roadmap.adapters.inbound.cli.issues.resolution import invoke, resolve_issue_id


@click.group("comment")
def comment_group() -> None:
    """Manage comments on issues."""


@click.command("add")
@click.argument("issue_id")
@click.argument("body")
@click.option("--author", "-a", default=None, help="Comment author")
@click.option("--reply-to", "-r", type=int, default=None, help="Parent comment ID")
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
) -> None:
    """Add a Markdown comment to an issue."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    comment = invoke(
        lambda: core.issue_mutations.add_comment(
            identity, author or getpass.getuser(), body, reply_to
        )
    )
    click.echo(f"Comment {comment.id} added to issue {identity} by {comment.author}")


@click.command("list")
@click.argument("issue_id")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.pass_context
@require_initialized
def list_comments(ctx: click.Context, issue_id: str, output_format: str) -> None:
    """List comments on an issue."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    comments = invoke(lambda: core.issue_queries.view(identity)).comments
    if output_format == "json":
        click.echo(
            json.dumps(
                [
                    {
                        "id": item.id,
                        "author": item.author,
                        "body": item.body,
                        "created_at": item.created_at.value.isoformat(),
                        "updated_at": item.updated_at.value.isoformat(),
                        "in_reply_to": item.in_reply_to,
                    }
                    for item in comments
                ],
                ensure_ascii=False,
            )
        )
        return
    if not comments:
        click.echo("No comments yet")
        return
    replies = {item.id: item.in_reply_to for item in comments}
    for item in comments:
        depth = 0
        parent = item.in_reply_to
        while parent is not None and depth < len(comments):
            depth += 1
            parent = replies.get(parent)
        prefix = "  " * depth
        click.echo(
            f"{prefix}#{item.id} @{item.author} {item.created_at.value:%Y-%m-%d %H:%M}"
        )
        click.echo(f"{prefix}{item.body}")


comment_group.add_command(add_comment, name="add")
comment_group.add_command(list_comments, name="list")
