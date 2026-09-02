"""Explicit retention cleanup for legacy backup files."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized


def _validate_retention_options(keep: int, days: int | None) -> None:
    if keep < 0:
        raise click.BadParameter("keep must be non-negative", param_hint="--keep")
    if days is not None and days < 0:
        raise click.BadParameter("days must be non-negative", param_hint="--days")


def _group_backups(backups_dir: Path) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in backups_dir.glob("*.backup.md") if backups_dir.exists() else ():
        parts = path.stem.split("_")
        grouped["_".join(parts[:-1])].append(path)
    return grouped


def _stale_paths(paths: list[Path], keep: int, cutoff: datetime | None) -> list[Path]:
    ordered = sorted(paths, key=lambda path: (-path.stat().st_mtime, path.name))
    stale: list[Path] = []
    for index, path in enumerate(ordered):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if index >= keep or (cutoff is not None and modified < cutoff):
            stale.append(path)
    return stale


def _candidates(
    backups_dir: Path, keep: int, days: int | None, now: datetime
) -> tuple[Path, ...]:
    _validate_retention_options(keep, days)
    grouped = _group_backups(backups_dir)
    cutoff = now - timedelta(days=days) if days is not None else None
    selected: list[Path] = []
    for paths in grouped.values():
        selected.extend(_stale_paths(paths, keep, cutoff))
    return tuple(sorted(selected))


def _diagnostic_matches(core, finding_id: str) -> tuple[str, ...]:
    report = core.health.scan()
    return tuple(
        finding.scope for finding in report.findings if finding.finding_id == finding_id
    )


def _selected_diagnostic_check(
    check_folders: bool, check_duplicates: bool, check_malformed: bool
) -> str | None:
    checks = {
        "canonical.noncanonical-path": check_folders,
        "canonical.duplicate-id": check_duplicates,
        "canonical.invalid": check_malformed,
    }
    selected = [name for name, enabled in checks.items() if enabled]
    if len(selected) > 1:
        raise click.UsageError("select only one --check-* option")
    return selected[0] if selected else None


def _report_diagnostic_matches(core, finding_id: str) -> None:
    matches = _diagnostic_matches(core, finding_id)
    click.echo("\n".join(matches) + ("\n" if matches else "No findings.\n"), nl=False)


def _remove_backups(candidates: tuple[Path, ...], relative: tuple[str, ...]) -> None:
    failures: list[str] = []
    for path, label in zip(candidates, relative, strict=True):
        try:
            path.unlink()
        except OSError as error:
            failures.append(f"{label}: {error}")
    if failures:
        raise click.ClickException(
            "Backup cleanup was incomplete:\n" + "\n".join(failures)
        )
    click.echo(f"Removed {len(candidates)} backup file(s).")


@click.command()
@click.option("--keep", type=int, default=10, show_default=True)
@click.option("--days", type=int)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--backups-only", is_flag=True)
@click.option("--check-folders", is_flag=True)
@click.option("--check-duplicates", is_flag=True)
@click.option("--check-malformed", is_flag=True)
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
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
) -> None:
    """Preview or remove only retention-qualified legacy backup files."""
    del backups_only, verbose
    diagnostic_check = _selected_diagnostic_check(
        check_folders, check_duplicates, check_malformed
    )
    if diagnostic_check is not None:
        _report_diagnostic_matches(ctx.obj["core"], diagnostic_check)
        return
    roadmap_dir = ctx.obj["core"].roadmap_dir
    candidates = _candidates(roadmap_dir / "backups", keep, days, datetime.now(UTC))
    relative = tuple(path.relative_to(roadmap_dir).as_posix() for path in candidates)
    if not candidates:
        click.echo("No backup files qualify for cleanup.")
        return
    heading = "Would remove" if dry_run else "Will remove"
    click.echo(f"{heading} {len(candidates)} backup file(s):")
    for path in relative:
        click.echo(f"- {path}")
    if dry_run:
        return
    if not force:
        click.confirm("Remove exactly these backup files?", abort=True, default=False)
    _remove_backups(candidates, relative)
