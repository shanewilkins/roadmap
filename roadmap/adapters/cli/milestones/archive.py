"""Archive milestone command - move closed milestones to archive."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.milestones.archive_class import MilestoneArchive
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)


@click.command()
@click.argument("milestone_name", required=False)
@click.option(
    "--all-closed",
    is_flag=True,
    help="Archive all closed milestones",
)
@click.option(
    "--list",
    "list_archived",
    is_flag=True,
    help="List archived milestones",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be archived without actually doing it",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information",
)
@click.pass_context
@verbose_output
@log_command("milestone_archive", entity_type="milestone", track_duration=True)
@require_initialized
def archive_milestone(
    ctx: click.Context,
    milestone_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: F841
):
    """Archive a milestone by moving it to .roadmap/archive/milestones/.

    This is a non-destructive operation that preserves milestone data while
    cleaning up the active workspace.

    Examples:
        roadmap milestone archive "v1.0"
        roadmap milestone archive --all-closed
        roadmap milestone archive --list
    """
    core = ctx.obj["core"]
    console = get_console()

    archive = MilestoneArchive(core, console)

    if list_archived:
        from pathlib import Path

        from roadmap.adapters.persistence.parser import MilestoneParser

        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "milestones"

        if not archive_dir.exists():
            console.print("📋 No archived milestones.", style="yellow")
            return

        archived_files = list(archive_dir.glob("*.md"))
        if not archived_files:
            console.print("📋 No archived milestones.", style="yellow")
            return

        console.print("\n📦 Archived Milestones:\n", style="bold blue")
        for file_path in sorted(archived_files):
            try:
                milestone = MilestoneParser.parse_milestone_file(file_path)
                console.print(
                    f"  • {milestone.name} ({milestone.status.value})", style="cyan"
                )
            except Exception:
                console.print(
                    f"  • {file_path.name} (error reading file)", style="yellow"
                )
        return

    # Validate arguments
    if not milestone_name and not all_closed:
        console.print(
            "❌ Error: Specify a milestone name or use --all-closed",
            style="bold red",
        )
        ctx.exit(1)

    if milestone_name and all_closed:
        console.print(
            "❌ Error: Specify only one of: milestone name or --all-closed",
            style="bold red",
        )
        ctx.exit(1)

    try:
        archive.execute(
            entity_id=milestone_name,
            all_closed=all_closed,
            dry_run=dry_run,
            force=force,
        )
    except Exception as e:
        console.print(f"❌ Archive operation failed: {str(e)}", style="bold red")
        ctx.exit(1)
