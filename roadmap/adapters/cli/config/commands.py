"""Configuration management commands."""

import click
from structlog import get_logger

from roadmap.common.configuration import ConfigLoader
from roadmap.common.console import get_console

logger = get_logger()
console = get_console()


@click.group("config")
def config():
    """Manage roadmap configuration."""


@config.command("view")
@click.option(
    "--project",
    is_flag=True,
    help="Show project-level config instead of user-level",
)
@click.option(
    "--level",
    type=click.Choice(["user", "project", "merged"], case_sensitive=False),
    default="merged",
    help="Which config level to view (default: merged)",
)
def view(project: bool, level: str):
    """View current configuration."""
    # Handle legacy --project flag
    if project:
        level = "project"

    try:
        if level == "user":
            config_obj = ConfigLoader.load_user_config()
            source = "User-level config (~/.roadmap/config.yaml)"
        elif level == "project":
            config_obj = ConfigLoader.load_project_config()
            source = "Project-level config (.roadmap/config.yaml)"
        else:  # merged
            config_obj = ConfigLoader.load_config()
            source = "Merged configuration (defaults + user + project)"

        if config_obj is None and level != "merged":
            console.print(f"[yellow]No {level} configuration file found.[/yellow]")
            return

        console.print(f"\n[bold blue]{source}[/bold blue]")
        console.print("=" * 60)

        if config_obj:
            # Pretty-print as YAML-like structure
            data = config_obj.model_dump(exclude_none=True)
            _print_config_dict(data, indent=0)
        else:
            console.print("[dim]Using all defaults[/dim]")

        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="bold red")
        raise click.ClickException(str(e)) from e


@config.command("get")
@click.argument("key")
def get_cmd(key: str):
    """Get a configuration value by key (e.g., 'export.directory')."""
    try:
        value = ConfigLoader.get_config_value(key)
        if value is None:
            console.print(
                f"[yellow]Configuration key '{key}' not found.[/yellow]",
                style="yellow",
            )
        else:
            console.print(f"[cyan]{key}[/cyan]: {value}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="bold red")
        raise click.ClickException(str(e)) from e


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--project",
    is_flag=True,
    help="Set in project-level config instead of user-level",
)
def set_cmd(key: str, value: str, project: bool):
    """Set a configuration value by key (e.g., 'export.format json')."""
    try:
        # Try to parse value as boolean or other types
        parsed_value = _parse_config_value(value)

        success = ConfigLoader.set_config_value(
            key, parsed_value, project_level=project
        )

        if success:
            level = "project" if project else "user"
            console.print(
                f"[green]✓[/green] Set [cyan]{key}[/cyan] = {parsed_value} in {level} config"
            )
        else:
            console.print(f"[red]✗[/red] Failed to set {key}", style="bold red")
            raise click.ClickException(f"Failed to set {key}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="bold red")
        raise click.ClickException(str(e)) from e


@config.command("reset")
@click.option(
    "--project",
    is_flag=True,
    help="Reset project-level config instead of user-level",
)
@click.confirmation_option(prompt="Are you sure you want to reset the configuration?")
def reset(project: bool):
    """Reset configuration to defaults."""
    try:
        if project:
            path = ConfigLoader.get_project_config_path()
            path.unlink(missing_ok=True)
            console.print(
                "[green]✓[/green] Reset project-level configuration", style="green"
            )
        else:
            path = ConfigLoader.get_user_config_path()
            path.unlink(missing_ok=True)
            console.print(
                "[green]✓[/green] Reset user-level configuration", style="green"
            )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="bold red")
        raise click.ClickException(str(e)) from e


def _print_config_dict(data: dict, indent: int = 0):
    """Pretty-print configuration dictionary.

    Args:
        data: Dictionary to print
        indent: Current indentation level
    """
    for key, value in data.items():
        if isinstance(value, dict):
            console.print(f"{'  ' * indent}[bold]{key}:[/bold]")
            _print_config_dict(value, indent + 1)
        else:
            console.print(f"{'  ' * indent}[cyan]{key}[/cyan]: {value}")


def _parse_config_value(value: str):
    """Parse string value to appropriate Python type.

    Args:
        value: String value to parse

    Returns:
        Parsed value (bool, int, float, or str)
    """
    # Try boolean
    if value.lower() in ("true", "yes", "on"):
        return True
    if value.lower() in ("false", "no", "off"):
        return False

    # Try integer
    try:
        return int(value)
    except ValueError as e:
        logger.debug(
            "int_conversion_failed",
            value=value,
            error=str(e),
            action="parse_config_value",
        )

    # Try float
    try:
        return float(value)
    except ValueError as e:
        logger.debug(
            "float_conversion_failed",
            value=value,
            error=str(e),
            action="parse_config_value",
        )

    # Return as string
    return value
