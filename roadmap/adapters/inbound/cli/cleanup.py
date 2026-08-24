"""Explicit retention cleanup for legacy backup files."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized


def _candidates(
    backups_dir: Path, keep: int, days: int | None, now: datetime
) -> tuple[Path, ...]:
    if keep < 0:
        raise click.BadParameter("keep must be non-negative", param_hint="--keep")
    if days is not None and days < 0:
        raise click.BadParameter("days must be non-negative", param_hint="--days")
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in backups_dir.glob("*.backup.md") if backups_dir.exists() else ():
        parts = path.stem.split("_")
        grouped["_".join(parts[:-1])].append(path)
    cutoff = now - timedelta(days=days) if days is not None else None
    selected: list[Path] = []
    for paths in grouped.values():
        ordered = sorted(paths, key=lambda path: (-path.stat().st_mtime, path.name))
        for index, path in enumerate(ordered):
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if index >= keep or (cutoff is not None and modified < cutoff):
                selected.append(path)
    return tuple(sorted(selected))


def _diagnostic_matches(core, finding_id: str) -> tuple[str, ...]:
    report = core.health.scan()
    return tuple(
        finding.scope for finding in report.findings if finding.finding_id == finding_id
    )


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
    checks = {
        "canonical.noncanonical-path": check_folders,
        "canonical.duplicate-id": check_duplicates,
        "canonical.invalid": check_malformed,
    }
    selected_checks = [name for name, enabled in checks.items() if enabled]
    if len(selected_checks) > 1:
        raise click.UsageError("select only one --check-* option")
    if selected_checks:
        matches = _diagnostic_matches(ctx.obj["core"], selected_checks[0])
        click.echo(
            "\n".join(matches) + ("\n" if matches else "No findings.\n"), nl=False
        )
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
