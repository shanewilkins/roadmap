"""Scoped configuration commands backed by Bootstrap-resolved files."""

from typing import Any

import click
import yaml


@click.group("config")
def config() -> None:
    """Manage versioned project policy and external user preferences."""


def _configuration(ctx: click.Context):
    return ctx.find_root().obj["core"].configuration


@config.command("view")
@click.option("--project", is_flag=True, help="Show project configuration.")
@click.option(
    "--level",
    type=click.Choice(["user", "project", "merged"], case_sensitive=False),
    default="merged",
    show_default=True,
)
@click.pass_context
def view(ctx: click.Context, project: bool, level: str) -> None:
    """View configuration without exposing secrets or machine paths."""
    if project:
        level = "project"
    store = _configuration(ctx)
    data = (
        {"project": store.view("project"), "user": store.view("user")}
        if level == "merged"
        else store.view(level)
    )
    click.echo(yaml.safe_dump(data, sort_keys=False).rstrip())


@config.command("get")
@click.argument("key")
@click.pass_context
def get_cmd(ctx: click.Context, key: str) -> None:
    """Get one declared configuration key."""
    try:
        value = _configuration(ctx).get(key)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    if value is None:
        raise click.ClickException(f"Configuration key '{key}' is not set.")
    click.echo(f"{key}: {value}")


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--project", is_flag=True, help="Write project-scoped policy.")
@click.pass_context
def set_cmd(ctx: click.Context, key: str, value: str, project: bool) -> None:
    """Set one key in its declared scope."""
    scope = "project" if project else "user"
    try:
        _configuration(ctx).set(key, _parse_config_value(value), scope)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Set {key} in {scope} configuration.")


@config.command("reset")
@click.option("--project", is_flag=True, help="Reset project-scoped policy.")
@click.confirmation_option(prompt="Are you sure you want to reset the configuration?")
@click.pass_context
def reset(ctx: click.Context, project: bool) -> None:
    """Reset only the selected configuration scope."""
    scope = "project" if project else "user"
    _configuration(ctx).reset(scope)
    click.echo(f"Reset {scope} configuration.")


def _parse_config_value(value: str) -> Any:
    """Parse a CLI scalar or YAML-style list without accepting mappings."""
    try:
        parsed = yaml.safe_load(value)
    except yaml.YAMLError:
        return value
    return parsed if isinstance(parsed, (str, int, float, bool, list)) else value
