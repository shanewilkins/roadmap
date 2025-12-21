"""Git hooks configuration command - Set up auto-sync behavior."""

from pathlib import Path

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.core.services.git_hook_auto_sync_service import (
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)

console = get_console()


@click.command(name="hooks-config")
@click.option(
    "--enable-auto-sync",
    is_flag=True,
    help="Enable auto-sync on Git events",
)
@click.option(
    "--disable-auto-sync",
    is_flag=True,
    help="Disable all auto-sync on Git events",
)
@click.option(
    "--sync-on-commit",
    is_flag=True,
    help="Enable auto-sync after commits",
)
@click.option(
    "--no-sync-on-commit",
    is_flag=True,
    help="Disable auto-sync after commits",
)
@click.option(
    "--sync-on-checkout",
    is_flag=True,
    help="Enable auto-sync on branch changes",
)
@click.option(
    "--no-sync-on-checkout",
    is_flag=True,
    help="Disable auto-sync on branch changes",
)
@click.option(
    "--sync-on-merge",
    is_flag=True,
    help="Enable auto-sync on merge operations",
)
@click.option(
    "--no-sync-on-merge",
    is_flag=True,
    help="Disable auto-sync on merge operations",
)
@click.option(
    "--confirm/--no-confirm",
    default=None,
    help="Require confirmation before syncing",
)
@click.option(
    "--force-local",
    is_flag=True,
    help="Resolve conflicts by keeping local changes",
)
@click.option(
    "--force-github",
    is_flag=True,
    help="Resolve conflicts by keeping GitHub changes",
)
@click.option(
    "--show",
    "show_config",
    is_flag=True,
    help="Show current configuration",
)
@click.pass_context
@require_initialized
def hooks_config(
    ctx: click.Context,
    enable_auto_sync: bool,
    disable_auto_sync: bool,
    sync_on_commit: bool,
    no_sync_on_commit: bool,
    sync_on_checkout: bool,
    no_sync_on_checkout: bool,
    sync_on_merge: bool,
    no_sync_on_merge: bool,
    confirm: bool | None,
    force_local: bool,
    force_github: bool,
    show_config: bool,
) -> None:
    """Configure Git hooks auto-sync behavior.

    Examples:
        # Show current configuration
        roadmap git hooks-config --show

        # Enable auto-sync on commits with confirmation
        roadmap git hooks-config --enable-auto-sync --sync-on-commit --confirm

        # Configure force-local resolution for conflicts
        roadmap git hooks-config --sync-on-commit --force-local

        # Disable auto-sync on checkouts
        roadmap git hooks-config --no-sync-on-checkout

    Configuration is stored locally in the roadmap project.
    """
    core = ctx.obj.get("core") if isinstance(ctx.obj, dict) else ctx.obj

    # Config file path
    config_path = Path.cwd() / ".roadmap" / "config.json"

    # Initialize service
    service = GitHookAutoSyncService(core)

    # Load existing config from storage if available
    service.load_config_from_file(config_path)
    current_config = service.get_config()

    # Build new config from options
    new_config = GitHookAutoSyncConfig(
        auto_sync_enabled=enable_auto_sync
        or (not disable_auto_sync and current_config.auto_sync_enabled),
        sync_on_commit=sync_on_commit
        or (not no_sync_on_commit and current_config.sync_on_commit),
        sync_on_checkout=sync_on_checkout
        or (not no_sync_on_checkout and current_config.sync_on_checkout),
        sync_on_merge=sync_on_merge
        or (not no_sync_on_merge and current_config.sync_on_merge),
        confirm_before_sync=(
            confirm if confirm is not None else current_config.confirm_before_sync
        ),
        force_local=force_local or current_config.force_local,
        force_github=force_github or current_config.force_github,
    )

    # Handle conflicts in resolution options
    if force_local and force_github:
        console.print("[red]❌ Cannot use both --force-local and --force-github[/red]")
        ctx.exit(1)

    # Apply new config
    service.set_config(new_config)

    # Save config to file if any settings changed
    if any(
        [
            enable_auto_sync,
            disable_auto_sync,
            sync_on_commit,
            no_sync_on_commit,
            sync_on_checkout,
            no_sync_on_checkout,
            sync_on_merge,
            no_sync_on_merge,
            confirm is not None,
            force_local,
            force_github,
        ]
    ):
        if service.save_config_to_file(config_path):
            console.print("[dim]Config saved to .roadmap/config.json[/dim]")

    # Show configuration
    if show_config or not any(
        [
            enable_auto_sync,
            disable_auto_sync,
            sync_on_commit,
            no_sync_on_commit,
            sync_on_checkout,
            no_sync_on_checkout,
            sync_on_merge,
            no_sync_on_merge,
            confirm is not None,
            force_local,
            force_github,
        ]
    ):
        _display_config(new_config, service)
    else:
        console.print("[green]✅ Configuration updated[/green]")
        _display_config(new_config, service)


def _display_config(
    config: GitHookAutoSyncConfig, service: GitHookAutoSyncService
) -> None:
    """Display current auto-sync configuration."""
    console.print()
    console.print("[bold cyan]Git Hooks Auto-Sync Configuration[/bold cyan]")
    console.print()

    # Check if config is persisted
    config_path = Path.cwd() / ".roadmap" / "config.json"
    if config_path.exists():
        console.print(f"[dim]Config file: {config_path}[/dim]")
        console.print()

    # Master switch
    master_status = (
        "[green]✓ ENABLED[/green]"
        if config.auto_sync_enabled
        else "[dim]✗ DISABLED[/dim]"
    )
    console.print(f"Master Switch:       {master_status}")
    console.print()

    # Per-event configuration
    console.print("[bold]Sync Events:[/bold]")
    _print_setting(
        "  Commit",
        config.sync_on_commit and config.auto_sync_enabled,
    )
    _print_setting(
        "  Branch Checkout",
        config.sync_on_checkout and config.auto_sync_enabled,
    )
    _print_setting(
        "  Merge",
        config.sync_on_merge and config.auto_sync_enabled,
    )
    console.print()

    # Behavior settings
    console.print("[bold]Behavior:[/bold]")
    console.print(
        f"  Confirm Before Sync: {'✓ Yes' if config.confirm_before_sync else '✗ No'}"
    )
    console.print()

    # Conflict resolution
    console.print("[bold]Conflict Resolution:[/bold]")
    if config.force_local:
        console.print("  Strategy: [yellow]Force Local (keep local changes)[/yellow]")
    elif config.force_github:
        console.print("  Strategy: [yellow]Force GitHub (keep remote changes)[/yellow]")
    else:
        console.print(
            "  Strategy: [dim]None configured (manual resolution required)[/dim]"
        )
    console.print()

    # Statistics
    try:
        stats = service.get_sync_stats()
        console.print("[bold]Sync Statistics:[/bold]")
        console.print(f"  Total Issues:       {stats['total_issues']}")
        console.print(
            f"  GitHub-Linked:      {stats['total_issues'] - stats['never_synced']}"
        )
        console.print(f"  Never Synced:       {stats['never_synced']}")
        if stats["total_sync_attempts"] > 0:
            console.print(f"  Success Rate:       {stats['success_rate']:.1f}%")
    except Exception:
        # Stats might fail if no issues exist
        pass

    console.print()


def _print_setting(label: str, enabled: bool) -> None:
    """Print a configuration setting with status."""
    status = "[green]✓ ENABLED[/green]" if enabled else "[dim]✗ disabled[/dim]"
    console.print(f"{label:25} {status}")
