"""Explicit preview and publication of committed GitHub closure decisions."""

import json
from dataclasses import asdict

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import invoke, require_initialized


@click.group()
def github() -> None:
    """Publish explicitly opted-in canonical decisions; authentication uses gh."""


@github.command("publish-closures")
@click.option(
    "--repo",
    required=True,
    help="GitHub OWNER/REPO; only matching targets are selected.",
)
@click.option(
    "--apply", is_flag=True, help="Write to GitHub; default is an offline preview."
)
@click.pass_context
@require_initialized
def publish_closures(ctx: click.Context, repo: str, apply: bool) -> None:
    """Read Git HEAD, ignoring uncommitted edits, and publish eligible closures."""
    results = invoke(lambda: ctx.obj["core"].github_closures.execute(repo, apply=apply))
    click.echo(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "roadmap.github-closures",
                "apply": apply,
                "publications": [
                    {**asdict(item), "result": result} for item, result in results
                ],
            },
            indent=2,
        )
    )
