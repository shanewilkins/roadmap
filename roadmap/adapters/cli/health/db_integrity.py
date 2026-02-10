"""Database integrity check command.

Checks that local issue files align with database state and baseline.
"""

from __future__ import annotations

import sqlite3

import click
from structlog import get_logger

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.persistence.parser.issue import IssueParser

logger = get_logger(__name__)


def _collect_local_issue_ids(issues_dir) -> tuple[set[str], list[tuple[str, str]]]:
    local_ids: set[str] = set()
    parse_errors: list[tuple[str, str]] = []
    for file_path in issues_dir.glob("**/*.md"):
        try:
            issue = IssueParser.parse_issue_file(file_path)
        except Exception as exc:
            parse_errors.append((str(file_path), str(exc)))
            continue
        issue_id = getattr(issue, "id", None)
        if issue_id:
            local_ids.add(str(issue_id))
    return local_ids, parse_errors


def _load_db_state(db_path) -> tuple[set[str], set[str], int] | None:
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        db_ids = {row["id"] for row in conn.execute("SELECT id FROM issues").fetchall()}
        baseline_ids = {
            row["issue_id"]
            for row in conn.execute("SELECT issue_id FROM sync_base_state").fetchall()
        }
        remote_links_count = conn.execute(
            "SELECT COUNT(*) FROM issue_remote_links"
        ).fetchone()[0]
        conn.close()
        return db_ids, baseline_ids, remote_links_count
    except Exception as exc:
        logger.warning(
            "db_integrity_query_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            severity="operational",
        )
        return None


def _build_report(
    local_ids: set[str],
    db_ids: set[str],
    baseline_ids: set[str],
    remote_links_count: int,
    parse_errors: list[tuple[str, str]],
) -> dict:
    missing_in_db = sorted(local_ids - db_ids)
    extra_in_db = sorted(db_ids - local_ids)
    baseline_missing_issue = sorted(baseline_ids - db_ids)
    issue_missing_baseline = sorted(db_ids - baseline_ids)

    return {
        "local_issue_files": len(local_ids),
        "db_issues": len(db_ids),
        "sync_base_state": len(baseline_ids),
        "remote_links": remote_links_count,
        "missing_in_db": len(missing_in_db),
        "extra_in_db": len(extra_in_db),
        "baseline_missing_issue": len(baseline_missing_issue),
        "issue_missing_baseline": len(issue_missing_baseline),
        "missing_in_db_ids": missing_in_db,
        "extra_in_db_ids": extra_in_db,
        "baseline_missing_issue_ids": baseline_missing_issue,
        "issue_missing_baseline_ids": issue_missing_baseline,
        "parse_errors": parse_errors,
    }


def _print_plain_report(report: dict, show_ids: bool, limit: int) -> None:
    click.echo("DB Integrity Report")
    click.echo(f"local_issue_files: {report['local_issue_files']}")
    click.echo(f"db_issues: {report['db_issues']}")
    click.echo(f"sync_base_state: {report['sync_base_state']}")
    click.echo(f"remote_links: {report['remote_links']}")
    click.echo(f"missing_in_db: {report['missing_in_db']}")
    click.echo(f"extra_in_db: {report['extra_in_db']}")
    click.echo(f"baseline_missing_issue: {report['baseline_missing_issue']}")
    click.echo(f"issue_missing_baseline: {report['issue_missing_baseline']}")
    click.echo(f"parse_errors: {len(report['parse_errors'])}")

    if show_ids and limit > 0:
        if report["missing_in_db_ids"]:
            click.echo("missing_in_db_ids:")
            for issue_id in report["missing_in_db_ids"][:limit]:
                click.echo(f"  {issue_id}")
        if report["extra_in_db_ids"]:
            click.echo("extra_in_db_ids:")
            for issue_id in report["extra_in_db_ids"][:limit]:
                click.echo(f"  {issue_id}")
        if report["baseline_missing_issue_ids"]:
            click.echo("baseline_missing_issue_ids:")
            for issue_id in report["baseline_missing_issue_ids"][:limit]:
                click.echo(f"  {issue_id}")
        if report["issue_missing_baseline_ids"]:
            click.echo("issue_missing_baseline_ids:")
            for issue_id in report["issue_missing_baseline_ids"][:limit]:
                click.echo(f"  {issue_id}")
        if report["parse_errors"]:
            click.echo("parse_errors:")
            for path, error in report["parse_errors"][:limit]:
                click.echo(f"  {path}: {error}")


@click.command(name="db-integrity")
@click.option(
    "--show-ids",
    is_flag=True,
    help="Show missing/extra ids (limited by --limit)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output results as JSON",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Max ids to display when using --show-ids",
)
@click.pass_context
@require_initialized
def db_integrity(
    ctx: click.Context, show_ids: bool, json_output: bool, limit: int
) -> None:
    """Check database integrity against local issue files."""
    core = ctx.obj["core"]
    issues_dir = core.roadmap_dir / "issues"
    db_path = core.db_dir / "state.db"

    if not issues_dir.exists():
        click.echo("No issues directory found.")
        return

    if not db_path.exists():
        click.echo("Database not found.")
        return

    local_ids, parse_errors = _collect_local_issue_ids(issues_dir)
    db_state = _load_db_state(db_path)
    if db_state is None:
        click.echo("Failed to read database state.")
        return
    db_ids, baseline_ids, remote_links_count = db_state
    report = _build_report(
        local_ids,
        db_ids,
        baseline_ids,
        remote_links_count,
        parse_errors,
    )

    if json_output:
        import json

        if show_ids and limit > 0:
            report["missing_in_db_ids"] = report["missing_in_db_ids"][:limit]
            report["extra_in_db_ids"] = report["extra_in_db_ids"][:limit]
            report["baseline_missing_issue_ids"] = report["baseline_missing_issue_ids"][
                :limit
            ]
            report["issue_missing_baseline_ids"] = report["issue_missing_baseline_ids"][
                :limit
            ]
            report["parse_errors"] = [
                {"path": path, "error": error}
                for path, error in report["parse_errors"][:limit]
            ]
        else:
            report["parse_errors"] = [
                {"path": path, "error": error} for path, error in report["parse_errors"]
            ]
        click.echo(json.dumps(report, indent=2))
        return

    _print_plain_report(report, show_ids, limit)
