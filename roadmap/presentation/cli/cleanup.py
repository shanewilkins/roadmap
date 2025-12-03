"""Cleanup command - comprehensive roadmap maintenance and optimization."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console

from roadmap.application.health import (
    scan_for_duplicate_issues,
    scan_for_folder_structure_issues,
    scan_for_malformed_files,
)

console = Console()


def fix_malformed_files(issues_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    """Fix common malformed YAML issues in issue files.

    Returns a dict with:
    - 'fixed_files': List of files that were fixed
    - 'errors': List of files that couldn't be fixed
    """
    result = {"fixed_files": [], "errors": []}

    if not issues_dir.exists():
        return result

    malformed_scan = scan_for_malformed_files(issues_dir)

    for file_rel in malformed_scan["malformed_files"]:
        file_path = issues_dir / file_rel

        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract frontmatter
            if not content.startswith("---"):
                result["errors"].append(file_rel)
                continue

            parts = content.split("---", 2)
            if len(parts) < 3:
                result["errors"].append(file_rel)
                continue

            frontmatter_str, markdown_content = parts[1], parts[2]

            # Parse and fix common issues
            try:
                frontmatter = yaml.safe_load(frontmatter_str)
            except yaml.YAMLError:
                result["errors"].append(file_rel)
                continue

            # Fix git_commits if it's a list of strings instead of dicts
            if "git_commits" in frontmatter and isinstance(
                frontmatter["git_commits"], list
            ):
                fixed_commits = []
                needs_fix = False
                for commit in frontmatter["git_commits"]:
                    if isinstance(commit, str):
                        # Convert string commit hash to dict
                        fixed_commits.append({"hash": commit})
                        needs_fix = True
                    else:
                        fixed_commits.append(commit)
                if needs_fix:
                    frontmatter["git_commits"] = fixed_commits

            # Fix git_branches if it's a list of dicts instead of strings
            if "git_branches" in frontmatter and isinstance(
                frontmatter["git_branches"], list
            ):
                fixed_branches = []
                needs_fix = False
                for branch in frontmatter["git_branches"]:
                    if isinstance(branch, dict):
                        # Convert dict to string - prefer 'name' field or use as is
                        if "name" in branch:
                            fixed_branches.append(branch["name"])
                        elif isinstance(branch, str):
                            fixed_branches.append(branch)
                        else:
                            fixed_branches.append(str(branch))
                        needs_fix = True
                    elif isinstance(branch, str):
                        fixed_branches.append(branch)
                    else:
                        # Convert any other type to string
                        fixed_branches.append(str(branch))
                        needs_fix = True
                if needs_fix:
                    frontmatter["git_branches"] = fixed_branches

            # Reconstruct the file
            fixed_frontmatter = yaml.dump(
                frontmatter, default_flow_style=False, sort_keys=False
            )
            fixed_content = f"---\n{fixed_frontmatter}---\n{markdown_content}"

            if not dry_run:
                file_path.write_text(fixed_content, encoding="utf-8")

            result["fixed_files"].append(file_rel)

        except Exception:
            result["errors"].append(file_rel)

    return result


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
@click.pass_context
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

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    roadmap_dir = Path.cwd() / ".roadmap"
    issues_dir = roadmap_dir / "issues"

    # Handle specific flag modes
    if check_folders:
        _handle_check_folders(issues_dir, roadmap_dir, core)
        return

    if check_duplicates:
        _handle_check_duplicates(issues_dir, roadmap_dir)
        return

    if check_malformed:
        _handle_check_malformed(issues_dir, roadmap_dir, dry_run, force)
        return

    # Default or backups-only mode: run comprehensive cleanup
    try:
        cleanup_results = {
            "backups_deleted": 0,
            "backups_freed_mb": 0.0,
            "issues_moved": 0,
            "duplicates_deleted": 0,
            "malformed_fixed": 0,
        }

        # 1. Clean up backups
        if _cleanup_backups(roadmap_dir, keep, days, dry_run, force):
            cleanup_results["backups_deleted"] += 1

        # 2. Move misplaced issues and duplicates (skip if backups-only)
        if not backups_only:
            if not dry_run:
                _resolve_folder_issues(issues_dir, roadmap_dir, core, force)
                _resolve_duplicates(issues_dir, roadmap_dir, force)

                # 3. Fix malformed YAML files
                result = fix_malformed_files(issues_dir, dry_run=False)
                if result["fixed_files"]:
                    cleanup_results["malformed_fixed"] = len(result["fixed_files"])
                    console.print(
                        f"✅ Fixed {len(result['fixed_files'])} malformed file(s)",
                        style="green",
                    )
            else:
                console.print(
                    "\n[DRY RUN] Folder and duplicate resolution skipped in preview mode"
                )

    except Exception as e:
        console.print(f"❌ Cleanup failed: {e}", style="bold red")
        ctx.exit(1)


def _handle_check_folders(issues_dir: Path, roadmap_dir: Path, core: object) -> None:
    """Check and report folder structure issues."""
    if not issues_dir.exists():
        console.print("📋 No issues directory found.", style="yellow")
        return

    issues = scan_for_folder_structure_issues(issues_dir, core)

    if not issues:
        console.print(
            "✅ All issues appear to be in correct folders.",
            style="green",
        )
        return

    if "misplaced" in issues and issues["misplaced"]:
        console.print(
            f"\n⚠️  Found {len(issues['misplaced'])} issue(s) in wrong folders:\n",
            style="bold yellow",
        )
        for item in issues["misplaced"]:
            console.print(f"  • {item['issue_id']}: {item['title']}", style="cyan")
            console.print(f"    Current: {item['current_location']}", style="dim")
            console.print(f"    Expected: {item['expected_location']}", style="dim")
        console.print()

    if "orphaned" in issues and issues["orphaned"]:
        console.print(
            f"\n⚠️  Found {len(issues['orphaned'])} orphaned issue(s):\n",
            style="bold yellow",
        )
        for item in issues["orphaned"]:
            console.print(f"  • {item['issue_id']}: {item['title']}", style="cyan")
            console.print(f"    Location: {item['location']}", style="dim")
        console.print()


def _handle_check_duplicates(issues_dir: Path, roadmap_dir: Path) -> None:
    """Check and report duplicate issues."""
    if not issues_dir.exists():
        console.print("📋 No issues directory found.", style="yellow")
        return

    duplicates = scan_for_duplicate_issues(issues_dir)

    if not duplicates:
        console.print(
            "✅ No duplicate issues found.",
            style="green",
        )
        return

    console.print(
        f"\n⚠️  Found {len(duplicates)} issue(s) with multiple copies:\n",
        style="bold yellow",
    )

    for issue_id, files in sorted(duplicates.items()):
        console.print(f"  Issue ID: {issue_id}", style="cyan")
        for file_path in sorted(files):
            console.print(f"    • {file_path.relative_to(roadmap_dir)}", style="dim")
        console.print()


def _handle_check_malformed(
    issues_dir: Path, roadmap_dir: Path, dry_run: bool, force: bool
) -> None:
    """Check and fix malformed YAML files."""
    if not issues_dir.exists():
        console.print("📋 No issues directory found.", style="yellow")
        return

    malformed = scan_for_malformed_files(issues_dir)

    if not malformed["malformed_files"]:
        console.print(
            "✅ No malformed YAML files found.",
            style="green",
        )
        return

    console.print(
        f"\n⚠️  Found {len(malformed['malformed_files'])} malformed file(s):\n",
        style="bold yellow",
    )

    for file_rel in malformed["malformed_files"]:
        console.print(f"  • {file_rel}", style="cyan")
    console.print()

    if dry_run:
        console.print("[DRY RUN] Would fix the above files", style="dim")
        return

    if not force:
        if not click.confirm("Fix malformed files?", default=True):
            console.print("Skipped.", style="yellow")
            return

    result = fix_malformed_files(issues_dir, dry_run=False)

    if result["fixed_files"]:
        console.print(
            f"✅ Fixed {len(result['fixed_files'])} file(s)",
            style="green",
        )
        for file_rel in result["fixed_files"]:
            console.print(f"  • {file_rel}", style="dim")

    if result["errors"]:
        console.print(
            f"⚠️  Could not fix {len(result['errors'])} file(s)",
            style="yellow",
        )
        for file_rel in result["errors"]:
            console.print(f"  • {file_rel}", style="dim")


def _cleanup_backups(
    roadmap_dir: Path, keep: int, days: int | None, dry_run: bool, force: bool
) -> bool:
    """Clean up old backup files. Returns True if backups were processed."""
    backups_dir = roadmap_dir / "backups"

    if not backups_dir.exists():
        console.print("📋 No backup directory found.", style="yellow")
        return False

    backup_files = list(backups_dir.glob("*.backup.md"))  # type: ignore[func-returns-value]
    if not backup_files:
        console.print("📋 No backup files found.", style="yellow")
        return False

    # Group backups by issue ID
    backups_by_issue = {}
    for backup_file in backup_files:
        parts = backup_file.stem.split("_")
        issue_key = "_".join(parts[:-1])

        if issue_key not in backups_by_issue:
            backups_by_issue[issue_key] = []

        stat = backup_file.stat()
        backups_by_issue[issue_key].append(
            {
                "path": backup_file,
                "mtime": datetime.fromtimestamp(stat.st_mtime),
                "size": stat.st_size,
            }
        )

    # Determine files to delete
    files_to_delete = []
    cutoff_date = datetime.now() - timedelta(days=days) if days else None

    for _issue_key, backups in backups_by_issue.items():
        backups.sort(key=lambda x: x["mtime"], reverse=True)

        for idx, backup in enumerate(backups):
            should_delete = False

            if idx >= keep:
                should_delete = True

            if cutoff_date and backup["mtime"] < cutoff_date:
                should_delete = True

            if should_delete:
                files_to_delete.append(backup)

    if not files_to_delete:
        console.print(
            "✅ No backup files need to be cleaned up.",
            style="green",
        )
        return False

    total_size = sum(f["size"] for f in files_to_delete)
    size_mb = total_size / (1024 * 1024)

    # Dry run mode
    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would delete {len(files_to_delete)} backup file(s) ({size_mb:.2f} MB):\n",
            style="bold blue",
        )
        for backup in files_to_delete:
            console.print(
                f"  • {backup['path'].name} ({backup['size']} bytes)",
                style="cyan",
            )
        console.print(
            f"\nWould free approximately {size_mb:.2f} MB of disk space.",
            style="green",
        )
        return True

    # Confirm deletion
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
            return False

    # Perform deletion
    deleted_count = 0
    failed_count = 0

    for backup in files_to_delete:
        try:
            backup["path"].unlink()
            deleted_count += 1
        except Exception as e:
            console.print(
                f"⚠️  Failed to delete {backup['path'].name}: {e}",
                style="yellow",
            )
            failed_count += 1

    console.print(
        f"\n✅ Cleaned up {deleted_count} backup file(s), freed ~{size_mb:.2f} MB",
        style="bold green",
    )
    if failed_count > 0:
        console.print(f"⚠️  {failed_count} file(s) failed to delete", style="yellow")

    return True


def _resolve_folder_issues(
    issues_dir: Path, roadmap_dir: Path, core: object, force: bool
) -> None:
    """Move misplaced and orphaned issues to correct folders."""
    if not issues_dir.exists():
        return

    issues = scan_for_folder_structure_issues(issues_dir, core)

    if not issues:
        return

    misplaced_count = len(issues.get("misplaced", []))
    orphaned_count = len(issues.get("orphaned", []))
    total = misplaced_count + orphaned_count

    if total == 0:
        return

    console.print(
        f"\n🔧 Resolving {total} issue(s) with folder structure problems:\n",
        style="bold blue",
    )

    moves_to_make = []

    if misplaced_count:
        console.print(
            f"  Moving {misplaced_count} issue(s) to milestone folders:",
            style="yellow",
        )
        for item in issues["misplaced"]:
            console.print(
                f"    {item['issue_id']}: {item['current_location']} → {item['expected_location']}",
                style="cyan",
            )
            moves_to_make.append(
                {
                    "from": Path(item["current_location"]),
                    "to": Path(item["expected_location"]),
                    "issue_id": item["issue_id"],
                }
            )

    if orphaned_count:
        console.print(f"  Moving {orphaned_count} issue(s) to backlog:", style="yellow")
        for item in issues["orphaned"]:
            backlog_dest = issues_dir / "backlog" / Path(item["location"]).name
            console.print(
                f"    {item['issue_id']}: {item['location']} → {backlog_dest}",
                style="cyan",
            )
            moves_to_make.append(
                {
                    "from": Path(item["location"]),
                    "to": backlog_dest,
                    "issue_id": item["issue_id"],
                }
            )

    if not moves_to_make:
        return

    # Confirm moves
    if not force:
        console.print(
            f"\n⚠️  About to move {len(moves_to_make)} file(s):",
            style="bold yellow",
        )

        if not click.confirm("\nProceed with moves?", default=False):
            console.print("❌ Cancelled.", style="yellow")
            return

    # Perform moves
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

    console.print(
        f"\n✅ Moved {moved_count} issue file(s) to correct folders",
        style="bold green",
    )
    if failed_count > 0:
        console.print(f"⚠️  {failed_count} file(s) failed to move", style="yellow")


def _resolve_duplicates(issues_dir: Path, roadmap_dir: Path, force: bool) -> None:
    """Resolve duplicate issues by keeping the latest version."""
    if not issues_dir.exists():
        return

    duplicates = scan_for_duplicate_issues(issues_dir)

    if not duplicates:
        return

    console.print(
        f"\n🔧 Resolving {len(duplicates)} duplicate issue(s) (keeping latest):\n",
        style="bold blue",
    )

    files_to_delete = []

    for issue_id, files in sorted(duplicates.items()):
        console.print(f"  Issue ID: {issue_id}", style="cyan")

        # Sort by modification time (newest first)
        sorted_files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)

        keeper = sorted_files[0]
        to_remove = sorted_files[1:]

        console.print(f"    Keeping: {keeper.relative_to(roadmap_dir)}", style="green")
        for f in to_remove:
            console.print(f"    Removing: {f.relative_to(roadmap_dir)}", style="red")
            files_to_delete.append(f)

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

    console.print(
        f"\n✅ Deleted {deleted_count} duplicate file(s)",
        style="bold green",
    )
    if failed_count > 0:
        console.print(f"⚠️  {failed_count} file(s) failed to delete", style="yellow")
