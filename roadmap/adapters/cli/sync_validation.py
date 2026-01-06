"""Sync validation commands for checking remote link health.

This module provides commands to validate and repair remote links in the database,
ensuring that all YAML remote_ids are properly tracked and accessible.
"""

import sys

import click

from roadmap.adapters.cli.helpers import require_initialized
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
    from roadmap.adapters.persistence.parser.issue import IssueParser

    core = ctx.obj["core"]
    console = get_console()

    try:
        # Get the state manager to access remote_link_repo
        state_manager = core.persistence.state_manager

        # Load all issues from YAML files
        issues_dir = core.issues_dir

        if not issues_dir.exists():
            console.print(
                f"❌ Issues directory not found: {issues_dir}",
                style="bold red",
            )
            sys.exit(1)

        # Collect all issue files
        issue_files = sorted(issues_dir.glob("**/*.md"))
        if not issue_files:
            console.print("ℹ️  No issue files found", style="yellow")
            return

        # Parse and validate all issues
        validation_report = {
            "total_files": len(issue_files),
            "files_with_remote_ids": 0,
            "database_links": 0,
            "discrepancies": [],
            "missing_in_db": [],
            "extra_in_db": [],
        }

        yaml_remote_ids = {}  # issue_id -> {backend -> remote_id}
        unparseable_files = []

        # First pass: load all YAML remote_ids
        for file_path in issue_files:
            try:
                issue = IssueParser.parse_issue_file(file_path)
                if issue.remote_ids:
                    yaml_remote_ids[issue.id] = issue.remote_ids
                    validation_report["files_with_remote_ids"] += 1
                    if verbose:
                        console.print(
                            f"  📄 {issue.id}: {', '.join(issue.remote_ids.keys())}",
                            style="cyan",
                        )
            except Exception as e:
                logger.warning(
                    "failed_to_parse_issue_file",
                    file_path=str(file_path),
                    error=str(e),
                )
                unparseable_files.append((str(file_path), str(e)))

        # Get all database links for GitHub (main backend)
        db_links = state_manager.remote_link_repo.get_all_links_for_backend("github")
        db_issue_uuids = {link.issue_uuid for link in db_links}
        validation_report["database_links"] = len(db_links)

        # Check for discrepancies
        yaml_issue_uuids = set(yaml_remote_ids.keys())

        # Issues in YAML but not in database
        for issue_uuid in yaml_issue_uuids:
            if issue_uuid not in db_issue_uuids:
                validation_report["missing_in_db"].append(issue_uuid)
                if verbose:
                    console.print(
                        f"  ⚠️  Missing in DB: {issue_uuid}",
                        style="yellow",
                    )

        # Links in database but not in YAML (might be archived)
        for link in db_links:
            if link.issue_uuid not in yaml_issue_uuids:
                validation_report["extra_in_db"].append(link.issue_uuid)
                if verbose:
                    console.print(
                        f"  ℹ️  In DB but not YAML: {link.issue_uuid} (may be archived)",
                        style="dim",
                    )

        # Display summary
        console.print(
            "\n[bold]Remote Links Validation Report[/bold]", style="bold cyan"
        )
        console.print(f"Total issue files: {validation_report['total_files']}")
        console.print(
            f"Files with remote_ids: {validation_report['files_with_remote_ids']}"
        )
        console.print(f"Database links: {validation_report['database_links']}")

        if validation_report["missing_in_db"]:
            console.print(
                f"\n[bold red]❌ Missing in database: {len(validation_report['missing_in_db'])}[/bold red]"
            )
            for issue_uuid in validation_report["missing_in_db"][:5]:
                console.print(f"  - {issue_uuid}")
            if len(validation_report["missing_in_db"]) > 5:
                console.print(
                    f"  ... and {len(validation_report['missing_in_db']) - 5} more"
                )

        if validation_report["extra_in_db"]:
            console.print(
                f"\n[bold yellow]⚠️  In database but not in YAML: {len(validation_report['extra_in_db'])}[/bold yellow]"
            )
            console.print("  (These may be archived issues)")

        if unparseable_files:
            console.print(
                f"\n[bold yellow]⚠️  Could not parse {len(unparseable_files)} files[/bold yellow]"
            )
            for file_path, error in unparseable_files[:3]:
                console.print(f"  - {file_path}: {error}")
            if len(unparseable_files) > 3:
                console.print(f"  ... and {len(unparseable_files) - 3} more")

        # Auto-fix if requested
        if auto_fix:
            _apply_auto_fix(
                state_manager,
                yaml_remote_ids,
                validation_report,
                console,
                dry_run,
                verbose,
            )

        # Exit with error if there are discrepancies
        if validation_report["missing_in_db"]:
            sys.exit(1)

        console.print(
            "\n✅ All remote links are valid and synchronized",
            style="bold green",
        )

    except Exception as e:
        logger.error(
            "validation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        console.print(f"❌ Validation failed: {str(e)}", style="bold red")
        sys.exit(1)


def _apply_auto_fix(
    state_manager,
    yaml_remote_ids: dict,
    validation_report: dict,
    console,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Apply automatic fixes for missing remote links.

    Args:
        state_manager: StateManager instance with access to repositories
        yaml_remote_ids: Dict of issue_uuid -> {backend -> remote_id}
        validation_report: Validation report dict to update
        console: Console instance for output
        dry_run: If True, don't actually apply changes
        verbose: If True, show detailed information
    """
    missing = validation_report["missing_in_db"]

    if not missing:
        console.print("\n✅ No links need fixing", style="bold green")
        return

    console.print(
        f"\n[bold cyan]🔧 Auto-fixing {len(missing)} missing links...[/bold cyan]"
    )

    if dry_run:
        console.print("  (Dry-run mode - no changes will be made)", style="dim yellow")

    fixed_count = 0
    for issue_uuid in missing:
        if issue_uuid not in yaml_remote_ids:
            continue

        remote_ids = yaml_remote_ids[issue_uuid]

        if not dry_run:
            # Import here to avoid circular dependencies
            try:
                for backend_name, remote_id in remote_ids.items():
                    state_manager.remote_link_repo.link_issue(
                        issue_uuid, backend_name, remote_id
                    )
                fixed_count += 1

                if verbose:
                    console.print(
                        f"  ✅ Fixed {issue_uuid}: {', '.join(remote_ids.keys())}",
                        style="green",
                    )
            except Exception as e:
                logger.warning(
                    "auto_fix_failed",
                    issue_uuid=issue_uuid,
                    error=str(e),
                )
                console.print(
                    f"  ⚠️  Failed to fix {issue_uuid}: {str(e)}",
                    style="yellow",
                )
        else:
            fixed_count += 1
            if verbose:
                console.print(
                    f"  → Would fix {issue_uuid}: {', '.join(remote_ids.keys())}",
                    style="dim cyan",
                )

    console.print(f"\n[bold green]✅ Fixed {fixed_count} remote links[/bold green]")

    if dry_run:
        console.print("Re-run without --dry-run to apply changes", style="dim yellow")
