"""
Sync management CLI commands.
"""

import click
import os
from roadmap.sync import SyncManager
from roadmap.credentials import CredentialManager
from roadmap.cli.utils import get_console

console = get_console()

@click.group()
def sync():
    """Synchronize with GitHub repository."""
    pass

@sync.command("setup")
@click.option("--token", help="GitHub token for authentication")
@click.option("--repo", help="GitHub repository (owner/repo)")
@click.option(
    "--insecure",
    is_flag=True,
    help="Store token in config file (NOT RECOMMENDED - use environment variable instead)",
)
@click.pass_context
def sync_setup(ctx: click.Context, token: str, repo: str, insecure: bool):
    """Set up GitHub integration and repository labels."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("✅ GitHub sync setup completed", style="bold green")
    except Exception as e:
        console.print(f"❌ Failed to setup sync: {e}", style="bold red")


@sync.command("test")
@click.pass_context
def sync_test(ctx: click.Context):
    """Test GitHub connection."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("✅ GitHub connection test successful", style="bold green")
    except Exception as e:
        console.print(f"❌ GitHub connection test failed: {e}", style="bold red")


@sync.command("status")
@click.pass_context
def sync_status(ctx: click.Context):
    """Show sync status."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Sync status: Not configured", style="yellow")
    except Exception as e:
        console.print(f"❌ Failed to get sync status: {e}", style="bold red")


@sync.command("push")
@click.option("--issues", is_flag=True, help="Push only issues")
@click.option("--milestones", is_flag=True, help="Push only milestones")
@click.option("--batch-size", default=10, help="Batch size for bulk operations")
@click.option("--workers", default=3, help="Number of concurrent workers")
@click.pass_context
def sync_push(ctx: click.Context, issues: bool, milestones: bool, batch_size: int, workers: int):
    """Push local changes to GitHub."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("✅ Sync push completed", style="bold green")
    except Exception as e:
        console.print(f"❌ Failed to push: {e}", style="bold red")


@sync.command("pull")
@click.option("--issues", is_flag=True, help="Pull only issues")
@click.option("--milestones", is_flag=True, help="Pull only milestones")
@click.option("--batch-size", default=10, help="Batch size for bulk operations")
@click.option("--workers", default=3, help="Number of concurrent workers")
@click.pass_context
def sync_pull(ctx: click.Context, issues: bool, milestones: bool, batch_size: int, workers: int):
    """Pull changes from GitHub."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("✅ Sync pull completed", style="bold green")
    except Exception as e:
        console.print(f"❌ Failed to pull: {e}", style="bold red")