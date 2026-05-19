"""Sync validation commands for checking remote link health.

This module provides commands to validate and repair remote links in the database,
ensuring that all YAML remote_ids are properly tracked and accessible.
"""

import sys

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


@click.command(name="validate-links")
@click.option(
    "--auto-fix",
    is_flag=True,
    help="Automatically repair broken or missing links",
)
@click.option(
    "--prune-extra",
    is_flag=True,
    help="Remove database links that are not present in YAML",
)
@click.option(
    "--dedupe",
    is_flag=True,
    help="Remove duplicate remote_id links (keep YAML-backed link if present)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying them",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed validation information for each issue",
)
@click.pass_context
@require_initialized
def validate_links(
    ctx: click.Context,
    auto_fix: bool,
    prune_extra: bool,
    dedupe: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Validate remote links in the database against YAML files.

    This command scans all YAML files to verify that remote_ids are:
    1. Properly loaded in the database
    2. Match between YAML source and database cache
    3. Valid and accessible for sync operations

    **Examples:**
        # Check link health
        roadmap sync validate-links

        # Show detailed info about each issue
        roadmap sync validate-links --verbose

        # Preview what would be fixed
        roadmap sync validate-links --auto-fix --dry-run

        # Repair broken links
        roadmap sync validate-links --auto-fix
    """
    core = ctx.obj["core"]
    console = get_console()

    try:
        issues_dir = core.issues_dir
        if not issues_dir.exists():
            console.print(
                f"❌ Issues directory not found: {issues_dir}", style="bold red"
            )
            sys.exit(1)

        validation_data = core.validation.collect_remote_link_validation_data(
            issues_dir
        )
        issue_files = validation_data["issue_files"]
        if not issue_files:
            console.print("ℹ️  No issue files found", style="yellow")
            return

        validation_report: dict = {
            "total_files": len(issue_files),
            "files_with_remote_ids": 0,
            "database_links": 0,
            "discrepancies": [],
            "missing_in_db": [],
            "extra_in_db": [],
            "duplicate_remote_ids": {},
        }
        yaml_remote_ids = validation_data["yaml_remote_ids"]
        unparseable_files = validation_data["unparseable_files"]
        db_links = validation_data["db_links"]
        validation_report.update(
            core.validation.build_remote_link_report(yaml_remote_ids, db_links)
        )

        _display_validation_summary(validation_report, unparseable_files, console)

        if auto_fix:
            _apply_auto_fix(
                core,
                yaml_remote_ids,
                validation_report,
                console,
                dry_run,
                verbose,
                prune_extra,
                dedupe,
            )

        if validation_report["missing_in_db"] and (not auto_fix or dry_run):
            sys.exit(1)

        console.print(
            "\n✅ All remote links are valid and synchronized", style="bold green"
        )

    except Exception as e:
        logger.error(
            "validation_failed",
            error=str(e),
            error_type=type(e).__name__,
            severity="system_error",
        )
        console.print(f"❌ Validation failed: {str(e)}", style="bold red")
        sys.exit(1)


def _display_validation_summary(
    validation_report: dict, unparseable_files: list, console
) -> None:
    """Print the remote-link validation summary to the console."""
    console.print("\n[bold]Remote Links Validation Report[/bold]", style="bold cyan")
    console.print(f"Total issue files: {validation_report['total_files']}")
    console.print(
        f"Files with remote_ids: {validation_report['files_with_remote_ids']}"
    )
    console.print(f"Database links: {validation_report['database_links']}")

    missing = validation_report["missing_in_db"]
    if missing:
        console.print(f"\n[bold red]❌ Missing in database: {len(missing)}[/bold red]")
        for issue_uuid in missing[:5]:
            console.print(f"  - {issue_uuid}")
        if len(missing) > 5:
            console.print(f"  ... and {len(missing) - 5} more")

    if validation_report["extra_in_db"]:
        console.print(
            f"\n[bold yellow]⚠️  In database but not in YAML: {len(validation_report['extra_in_db'])}[/bold yellow]"
        )
        console.print("  (These may be archived issues)")

    dup_ids = validation_report["duplicate_remote_ids"]
    if dup_ids:
        console.print(
            f"\n[bold yellow]⚠️  Duplicate remote IDs: {len(dup_ids)}[/bold yellow]"
        )
        for remote_id, issue_uuids in list(dup_ids.items())[:5]:
            console.print(f"  - {remote_id}: {', '.join(issue_uuids)}", style="dim")
        if len(dup_ids) > 5:
            console.print(f"  ... and {len(dup_ids) - 5} more")

    if unparseable_files:
        console.print(
            f"\n[bold yellow]⚠️  Could not parse {len(unparseable_files)} files[/bold yellow]"
        )
        for file_path, error in unparseable_files[:3]:
            console.print(f"  - {file_path}: {error}")
        if len(unparseable_files) > 3:
            console.print(f"  ... and {len(unparseable_files) - 3} more")


def _apply_auto_fix(
    core,
    yaml_remote_ids: dict,
    validation_report: dict,
    console,
    dry_run: bool,
    verbose: bool,
    prune_extra: bool,
    dedupe: bool,
) -> None:
    """Apply automatic fixes for missing remote links.

    Args:
        core: RoadmapCore instance with validation coordinator
        yaml_remote_ids: Dict of issue_uuid -> {backend -> remote_id}
        validation_report: Validation report dict to update
        console: Console instance for output
        dry_run: If True, don't actually apply changes
        verbose: If True, show detailed information
        prune_extra: If True, remove links missing from YAML
        dedupe: If True, remove duplicate remote IDs
    """
    missing = validation_report["missing_in_db"]
    if not missing and not prune_extra and not dedupe:
        console.print("\n✅ No links need fixing", style="bold green")
        return

    if missing:
        console.print(
            f"\n[bold cyan]🔧 Auto-fixing {len(missing)} missing links...[/bold cyan]"
        )
        if dry_run:
            console.print(
                "  (Dry-run mode - no changes will be made)", style="dim yellow"
            )
    if verbose and yaml_remote_ids:
        for issue_uuid, remote_ids in yaml_remote_ids.items():
            console.print(
                f"  📄 {issue_uuid}: {', '.join(remote_ids.keys())}", style="cyan"
            )
    if prune_extra and validation_report.get("extra_in_db"):
        console.print(
            f"\n[bold cyan]🧹 Removing {len(validation_report['extra_in_db'])} extra links...[/bold cyan]"
        )
    if dedupe and validation_report.get("duplicate_remote_ids"):
        console.print(
            f"\n[bold cyan]🧹 Removing {len(validation_report['duplicate_remote_ids'])} duplicate remote IDs...[/bold cyan]"
        )

    try:
        results = core.validation.apply_remote_link_fixes(
            yaml_remote_ids,
            validation_report,
            backend_name="github",
            prune_extra=prune_extra,
            dedupe=dedupe,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.warning("auto_fix_failed", error=str(e), severity="operational")
        console.print(f"  ⚠️  Auto-fix failed: {str(e)}", style="yellow")
        return

    if results.get("fixed_count"):
        console.print(
            f"\n[bold green]✅ Fixed {results['fixed_count']} missing remote links[/bold green]"
        )
    if results.get("removed_count"):
        console.print(
            f"[bold green]✅ Removed {results['removed_count']} extra remote links[/bold green]"
        )
    if results.get("deduped_count"):
        console.print(
            f"[bold green]✅ Removed {results['deduped_count']} duplicate remote links[/bold green]"
        )
    if dry_run:
        console.print("Re-run without --dry-run to apply changes", style="dim yellow")
