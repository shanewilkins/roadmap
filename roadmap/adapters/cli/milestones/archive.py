"""Archive milestone command - move closed milestones to archive."""

import shutil
from pathlib import Path

import click
from rich.console import Console

from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    verbose_output,
)

console = Console()


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
def archive_milestone(
    ctx: click.Context,
    milestone_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Archive a milestone by moving it to .roadmap/archive/milestones/.

    This is a non-destructive operation that preserves milestone data while
    cleaning up the active workspace. Archived milestones can be restored
    if needed.

    Examples:
        roadmap milestone archive "v1.0"
        roadmap milestone archive --all-closed
        roadmap milestone archive --all-closed --dry-run
        roadmap milestone archive --list
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    # Handle --list option
    if list_archived:
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
        for file_path in archived_files:
            try:
                milestone = MilestoneParser.parse_milestone_file(file_path)
                console.print(
                    f"  • {milestone.name} ({milestone.status.value})", style="cyan"
                )
            except Exception:
                console.print(f"  • {file_path.stem} (parse error)", style="red")
        return

    if not milestone_name and not all_closed:
        console.print(
            "❌ Error: Specify a milestone name or use --all-closed",
            style="bold red",
        )
        ctx.exit(1)

    if milestone_name and all_closed:
        console.print(
            "❌ Error: Cannot specify milestone name with --all-closed",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "milestones"

        if all_closed:
            # Get all milestones and filter for closed ones
            all_milestones = core.milestones.list()
            milestones = [m for m in all_milestones if m.status.value == "closed"]

            if not milestones:
                console.print("📋 No closed milestones to archive.", style="yellow")
                return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would archive {len(milestones)} milestone(s):\n",
                    style="bold blue",
                )
                for m in milestones:
                    console.print(f"  • {m.name}", style="cyan")
                return

            # Confirm
            if not force:
                console.print(
                    f"\n⚠️  About to archive {len(milestones)} closed milestone(s):",
                    style="bold yellow",
                )
                for m in milestones:
                    console.print(f"  • {m.name}", style="cyan")

                if not click.confirm("\nProceed with archival?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Archive each milestone
            ensure_directory_exists(archive_dir)
            archive_issues_dir = roadmap_dir / "archive" / "issues"
            archived_count = 0

            for milestone in milestones:
                # Find the milestone file by searching
                milestone_file = None
                for md_file in (roadmap_dir / "milestones").glob("*.md"):
                    try:
                        test_milestone = MilestoneParser.parse_milestone_file(md_file)
                        if test_milestone.name == milestone.name:
                            milestone_file = md_file
                            break
                    except Exception:
                        continue

                if milestone_file and milestone_file.exists():
                    archive_file = archive_dir / milestone_file.name
                    milestone_file.rename(archive_file)

                    # Also move associated issues folder if it exists
                    issues_dir = roadmap_dir / "issues" / milestone.name
                    if issues_dir.exists():
                        ensure_directory_exists(archive_issues_dir)
                        dest_issues_dir = archive_issues_dir / milestone.name
                        # Remove destination if it already exists
                        if dest_issues_dir.exists():
                            shutil.rmtree(dest_issues_dir)
                        issues_dir.rename(dest_issues_dir)

                    # Mark as archived in database
                    try:
                        core.db.mark_milestone_archived(milestone.name, archived=True)
                    except Exception as e:
                        console.print(
                            f"⚠️  Warning: Failed to mark milestone {milestone.name} as archived in database: {e}",
                            style="yellow",
                        )

                    archived_count += 1

            console.print(
                f"\n✅ Archived {archived_count} milestone(s) to .roadmap/archive/milestones/",
                style="bold green",
            )

        else:
            # Archive single milestone
            milestone = core.milestones.get(milestone_name)
            if not milestone:
                console.print(
                    f"❌ Milestone '{milestone_name}' not found.", style="bold red"
                )
                ctx.exit(1)

            assert milestone_name is not None

            if milestone.status.value != "closed":
                console.print(
                    f"⚠️  Warning: Milestone '{milestone_name}' is not closed (status: {milestone.status.value})",
                    style="bold yellow",
                )
                if not force and not click.confirm("Archive anyway?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would archive milestone: {milestone_name}",
                    style="bold blue",
                )
                console.print(
                    f"  Source: .roadmap/milestones/{milestone_name}.md",
                    style="cyan",
                )
                console.print(
                    f"  Destination: .roadmap/archive/milestones/{milestone_name}.md",
                    style="cyan",
                )
                return

            # Confirm
            if not force:
                if not click.confirm(
                    f"Archive milestone '{milestone_name}'?", default=False
                ):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Perform archive
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Find the milestone file by searching all .md files
            milestone_file = None
            for md_file in (roadmap_dir / "milestones").glob("*.md"):
                # Read and check if this is the right milestone
                try:
                    test_milestone = MilestoneParser.parse_milestone_file(md_file)
                    if test_milestone.name == milestone_name:
                        milestone_file = md_file
                        break
                except Exception:
                    continue

            if not milestone_file or not milestone_file.exists():
                console.print(
                    f"❌ Milestone file not found for: {milestone_name}",
                    style="bold red",
                )
                ctx.exit(1)

            archive_file = archive_dir / milestone_file.name
            milestone_file.rename(archive_file)

            # Also move associated issues folder if it exists
            issues_dir = roadmap_dir / "issues" / milestone_name
            archive_issues_dir = roadmap_dir / "archive" / "issues"
            if issues_dir.exists():
                ensure_directory_exists(archive_issues_dir)
                dest_issues_dir = archive_issues_dir / milestone_name
                # Remove destination if it already exists
                if dest_issues_dir.exists():
                    shutil.rmtree(dest_issues_dir)
                issues_dir.rename(dest_issues_dir)
                console.print(
                    f"  Moved issues to .roadmap/archive/issues/{milestone_name}/",
                    style="dim",
                )

            # Mark as archived in database
            try:
                core.db.mark_milestone_archived(milestone_name, archived=True)
            except Exception as e:
                console.print(
                    f"⚠️  Warning: Failed to mark in database: {e}", style="yellow"
                )

            console.print(
                f"\n✅ Archived milestone '{milestone_name}' to .roadmap/archive/milestones/",
                style="bold green",
            )

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_archive",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to archive milestone: {e}", style="bold red")
        ctx.exit(1)
