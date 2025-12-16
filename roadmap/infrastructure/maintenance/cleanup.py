"""Cleanup command - comprehensive roadmap maintenance and optimization."""

from pathlib import Path

import click

from roadmap.adapters.cli.presentation.cleanup_presenter import CleanupPresenter
from roadmap.common.cli_models import CleanupParams
from roadmap.common.console import get_console
from roadmap.core.services.backup_cleanup_service import BackupCleanupService
from roadmap.core.services.file_repair_service import FileRepairService
from roadmap.core.services.validators import (
    DataIntegrityValidator,
    DuplicateIssuesValidator,
    FolderStructureValidator,
)
from roadmap.infrastructure.logging import verbose_output

console = get_console()


@click.command()
@click.option(
    "--keep",
    type=int,
    default=10,
    help="Number of most recent backups to keep per issue (default: 10)",
)
@click.option(
    "--days",
    type=int,
    help="Delete backups older than this many days (default: no age-based limit)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview all cleanup actions without making changes",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.option(
    "--backups-only",
    is_flag=True,
    help="Only clean up old backup files (skip folder and duplicate fixes)",
)
@click.option(
    "--check-folders",
    is_flag=True,
    help="Only check/report folder structure issues",
)
@click.option(
    "--check-duplicates",
    is_flag=True,
    help="Only check/report duplicate issues",
)
@click.option(
    "--check-malformed",
    is_flag=True,
    help="Only check/report malformed YAML files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information",
)
@click.pass_context
@verbose_output
def cleanup(
    ctx: click.Context,
    keep: int,
    days: int | None,
    dry_run: bool,
    force: bool,
    backups_only: bool,
    check_folders: bool,
    check_duplicates: bool,
    check_malformed: bool,
    verbose: bool,
):
    """Comprehensive roadmap cleanup - fix backups, folders, duplicates, and malformed files.

    By default, performs all cleanup operations:
    1. Removes old backup files (keeps 10 most recent per issue)
    2. Moves misplaced issues to correct milestone folders
    3. Resolves duplicate issues (keeps latest version)
    4. Fixes malformed YAML in issue files

    Use --dry-run to preview all changes without making them.
    Use --force to skip confirmation prompts.

    Use individual options to target specific cleanup tasks:
    - --backups-only: Only clean up old backups
    - --check-folders: Only report folder structure issues
    - --check-duplicates: Only report duplicate issues
    - --check-malformed: Only report and fix malformed files

    Examples:
        roadmap cleanup                    # Fix everything interactively
        roadmap cleanup --dry-run          # Preview all changes
        roadmap cleanup --force            # Fix everything without prompting
        roadmap cleanup --backups-only     # Only clean up backups
        roadmap cleanup --check-folders    # Only check folder issues
        roadmap cleanup --check-malformed  # Only fix malformed YAML
    """
    core = ctx.obj["core"]
    presenter = CleanupPresenter()

    # Create structured parameter object
    params = CleanupParams(
        keep=keep,
        days=days,
        dry_run=dry_run,
        force=force,
        backups_only=backups_only,
        check_folders=check_folders,
        check_duplicates=check_duplicates,
        check_malformed=check_malformed,
        verbose=verbose,
    )

    if not core.is_initialized():
        presenter.present_no_roadmap()
        ctx.exit(1)

    roadmap_dir = Path.cwd() / ".roadmap"
    issues_dir = roadmap_dir / "issues"

    # Handle specific flag modes
    if params.check_folders:
        _handle_check_folders(issues_dir, roadmap_dir, core, presenter)
        return

    if params.check_duplicates:
        _handle_check_duplicates(issues_dir, roadmap_dir, presenter)
        return

    if params.check_malformed:
        _handle_check_malformed(
            issues_dir, roadmap_dir, params.dry_run, params.force, presenter
        )
        return

    # Default or backups-only mode: run comprehensive cleanup
    try:
        # 1. Clean up backups
        _run_backup_cleanup(
            roadmap_dir,
            params.keep,
            params.days,
            params.dry_run,
            params.force,
            presenter,
        )

        # 2. Move misplaced issues and duplicates (skip if backups-only)
        if not params.backups_only:
            if not params.dry_run:
                _resolve_folder_issues(issues_dir, roadmap_dir, core, force, presenter)
                _resolve_duplicates(issues_dir, roadmap_dir, force, presenter)

                # 3. Fix malformed YAML files
                _fix_malformed_files(issues_dir, presenter)
            else:
                presenter.present_dry_run_skipped()

    except Exception as e:
        presenter.present_cleanup_error(str(e))
        ctx.exit(1)


def _handle_check_folders(
    issues_dir: Path, roadmap_dir: Path, core: object, presenter: CleanupPresenter
) -> None:
    """Check and report folder structure issues."""
    if not issues_dir.exists():
        presenter.present_no_issues_dir()
        return

    issues = FolderStructureValidator.scan_for_folder_structure_issues(issues_dir, core)

    if not issues:
        presenter.present_folder_check_clean()
        return

    presenter.present_folder_issues(issues)


def _handle_check_duplicates(
    issues_dir: Path, roadmap_dir: Path, presenter: CleanupPresenter
) -> None:
    """Check and report duplicate issues."""
    if not issues_dir.exists():
        presenter.present_no_issues_dir()
        return

    duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)

    if not duplicates:
        presenter.present_duplicates_check_clean()
        return

    presenter.present_duplicate_issues(duplicates, roadmap_dir)


def _handle_check_malformed(
    issues_dir: Path,
    roadmap_dir: Path,
    dry_run: bool,
    force: bool,
    presenter: CleanupPresenter,
) -> None:
    """Check and fix malformed YAML files."""
    if not issues_dir.exists():
        presenter.present_no_issues_dir()
        return

    malformed = DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)

    if not malformed["malformed_files"]:
        presenter.present_malformed_check_clean()
        return

    presenter.present_malformed_files(malformed["malformed_files"])

    if dry_run:
        console.print("[DRY RUN] Would fix the above files", style="dim")
        return

    if not force:
        if not click.confirm("Fix malformed files?", default=True):
            console.print("Skipped.", style="yellow")
            return

    repair_service = FileRepairService()
    result = repair_service.repair_files(
        issues_dir, malformed["malformed_files"], dry_run=False
    )
    presenter.present_malformed_repair_result(result)


def _run_backup_cleanup(
    roadmap_dir: Path,
    keep: int,
    days: int | None,
    dry_run: bool,
    force: bool,
    presenter: CleanupPresenter,
) -> None:
    """Run backup cleanup using service."""
    backup_service = BackupCleanupService()

    # Get files that would be deleted
    backups_dir = roadmap_dir / "backups"
    if not backups_dir.exists():
        presenter.present_no_backups()
        return

    files_to_delete = backup_service._select_backups_for_deletion(
        backups_dir, keep, days
    )

    if not files_to_delete:
        presenter.present_no_cleanup_needed()
        return

    # Dry run: show what would be deleted
    if dry_run:
        presenter.present_backup_cleanup_dry_run(list(files_to_delete))  # type: ignore
        return

    # Confirm deletion
    total_size = sum(f["size"] for f in files_to_delete)
    size_mb = total_size / (1024 * 1024)

    if not force:
        console.print(
            f"\n⚠️  About to delete {len(files_to_delete)} backup file(s) ({size_mb:.2f} MB):",
            style="bold yellow",
        )
        console.print(
            f"  This will free approximately {size_mb:.2f} MB of disk space.",
            style="yellow",
        )

        if not click.confirm("\nProceed with cleanup?", default=False):
            console.print("❌ Cancelled.", style="yellow")
            return

    # Perform cleanup
    result = backup_service.cleanup_backups(roadmap_dir, keep, days, dry_run=False)
    presenter.present_backup_cleanup_result(result)


def _build_move_list(issues_dir: Path, issues: dict) -> list:
    """Build list of moves to make from issue structure issues.

    Args:
        issues_dir: Path to issues directory
        issues: Dictionary of misplaced and orphaned issues

    Returns:
        List of move operations
    """
    moves_to_make = []

    if issues.get("misplaced"):
        for item in issues["misplaced"]:
            moves_to_make.append(
                {
                    "from": Path(item["current_location"]),
                    "to": Path(item["expected_location"]),
                    "issue_id": item["issue_id"],
                }
            )

    if issues.get("orphaned"):
        for item in issues["orphaned"]:
            backlog_dest = issues_dir / "backlog" / Path(item["location"]).name
            moves_to_make.append(
                {
                    "from": Path(item["location"]),
                    "to": backlog_dest,
                    "issue_id": item["issue_id"],
                }
            )

    return moves_to_make


def _confirm_folder_moves(force: bool) -> bool:
    """Confirm folder moves with user.

    Args:
        force: Skip confirmation if True

    Returns:
        True if user confirmed or force is True
    """
    if force:
        return True

    console.print(
        "\n⚠️  About to move files:",
        style="bold yellow",
    )
    return click.confirm("\nProceed with moves?", default=False)


def _perform_folder_moves(moves_to_make: list) -> tuple[int, int]:
    """Perform folder move operations.

    Args:
        moves_to_make: List of move operations to perform

    Returns:
        Tuple of (moved_count, failed_count)
    """
    moved_count = 0
    failed_count = 0

    for move in moves_to_make:
        try:
            move["to"].parent.mkdir(parents=True, exist_ok=True)
            move["from"].rename(move["to"])
            moved_count += 1
        except Exception as e:
            console.print(
                f"⚠️  Failed to move {move['from'].name}: {e}",
                style="yellow",
            )
            failed_count += 1

    return moved_count, failed_count


def _resolve_folder_issues(
    issues_dir: Path,
    roadmap_dir: Path,
    core: object,
    force: bool,
    presenter: CleanupPresenter,
) -> None:
    """Move misplaced and orphaned issues to correct folders."""
    if not issues_dir.exists():
        return

    issues = FolderStructureValidator.scan_for_folder_structure_issues(issues_dir, core)

    if not issues:
        return

    misplaced_count = len(issues.get("misplaced", []))
    orphaned_count = len(issues.get("orphaned", []))
    total = misplaced_count + orphaned_count

    if total == 0:
        return

    moves_to_make = _build_move_list(issues_dir, issues)

    if not moves_to_make:
        return

    presenter.present_folder_moves(moves_to_make)

    # Confirm moves
    if not _confirm_folder_moves(force):
        console.print("❌ Cancelled.", style="yellow")
        return

    # Perform moves
    moved_count, failed_count = _perform_folder_moves(moves_to_make)
    presenter.present_folder_moves_result(moved_count, failed_count)


def _resolve_duplicates(
    issues_dir: Path, roadmap_dir: Path, force: bool, presenter: CleanupPresenter
) -> None:
    """Resolve duplicate issues by keeping the latest version."""
    if not issues_dir.exists():
        return

    duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)

    if not duplicates:
        return

    presenter.present_duplicate_resolution(duplicates, roadmap_dir)

    files_to_delete = []

    for _issue_id, files in sorted(duplicates.items()):
        # Sort by modification time (newest first)
        sorted_files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
        to_remove = sorted_files[1:]
        files_to_delete.extend(to_remove)

    if not files_to_delete:
        return

    # Confirm deletion
    if not force:
        console.print(
            f"\n⚠️  About to delete {len(files_to_delete)} duplicate file(s):",
            style="bold yellow",
        )

        if not click.confirm("\nProceed with deletion?", default=False):
            console.print("❌ Cancelled.", style="yellow")
            return

    # Perform deletion
    deleted_count = 0
    failed_count = 0

    for f in files_to_delete:
        try:
            f.unlink()
            deleted_count += 1
        except Exception as e:
            console.print(
                f"⚠️  Failed to delete {f.name}: {e}",
                style="yellow",
            )
            failed_count += 1

    presenter.present_duplicate_resolution_result(deleted_count, failed_count)


def _fix_malformed_files(issues_dir: Path, presenter: CleanupPresenter) -> None:
    """Fix malformed YAML files in issues directory."""
    malformed = DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)

    if not malformed["malformed_files"]:
        return

    repair_service = FileRepairService()
    result = repair_service.repair_files(
        issues_dir, malformed["malformed_files"], dry_run=False
    )
    presenter.present_malformed_repair_result(result)
