#!/usr/bin/env python3
"""Analyze roadmap JSON logs for errors, slow operations, and command usage patterns.

Usage:
    python scripts/analyze_logs.py
    python scripts/analyze_logs.py --log-file ~/.roadmap/logs/roadmap.log
    python scripts/analyze_logs.py --errors-only
    python scripts/analyze_logs.py --slow-ops --threshold 1000
    python scripts/analyze_logs.py --command create_issue
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import click


def parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse a JSON log line."""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


@click.command()
@click.option(
    "--log-file",
    type=click.Path(exists=True),
    default=str(Path.home() / ".roadmap" / "logs" / "roadmap.log"),
    help="Path to log file",
)
@click.option("--errors-only", is_flag=True, help="Show only error entries")
@click.option("--slow-ops", is_flag=True, help="Show slow operations above threshold")
@click.option(
    "--threshold",
    type=int,
    default=500,
    help="Slow operation threshold in milliseconds (default: 500ms)",
)
@click.option("--command", type=str, help="Filter by specific command/operation name")
@click.option(
    "--correlation-id",
    type=str,
    help="Filter by correlation ID to trace a single request",
)
@click.option("--recent", type=int, help="Show only last N entries")
def analyze_logs(
    log_file: str,
    errors_only: bool,
    slow_ops: bool,
    threshold: int,
    command: str | None,
    correlation_id: str | None,
    recent: int | None,
):
    """Analyze roadmap JSON logs for patterns and issues."""

    log_path = Path(log_file)
    if not log_path.exists():
        click.echo(f"❌ Log file not found: {log_path}", err=True)
        sys.exit(1)

    click.echo(f"📊 Analyzing logs from: {log_path}\n")

    # Read and parse logs
    entries = []
    with open(log_path) as f:
        for line in f:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)

    if not entries:
        click.echo("⚠️  No valid log entries found")
        return

    # Apply filters
    filtered = entries

    if correlation_id:
        filtered = [e for e in filtered if e.get("correlation_id") == correlation_id]
        click.echo(f"🔍 Filtering by correlation ID: {correlation_id}")

    if command:
        filtered = [e for e in filtered if e.get("operation") == command]
        click.echo(f"🔍 Filtering by command: {command}")

    if errors_only:
        filtered = [e for e in filtered if e.get("level") in ("error", "critical")]
        click.echo("🔍 Filtering errors only")

    if slow_ops:
        filtered = [e for e in filtered if e.get("duration_ms", 0) > threshold]
        click.echo(f"🔍 Filtering slow operations (>{threshold}ms)")

    if recent:
        filtered = filtered[-recent:]
        click.echo(f"🔍 Showing last {recent} entries")

    if not filtered:
        click.echo("⚠️  No entries match the filters")
        return

    # Display results based on mode
    if correlation_id:
        display_correlation_trace(filtered)
    elif errors_only:
        display_errors(filtered)
    elif slow_ops:
        display_slow_operations(filtered, threshold)
    else:
        display_summary(filtered)


def display_summary(entries: list[dict[str, Any]]):
    """Display comprehensive summary of log entries."""
    click.echo("\n" + "=" * 80)
    click.echo("📈 LOG SUMMARY")
    click.echo("=" * 80)

    # Count by level
    levels = Counter(e.get("level", "unknown") for e in entries)
    click.echo("\n📊 Entries by level:")
    for level, count in levels.most_common():
        emoji = {
            "debug": "🐛",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🔥",
        }.get(level, "•")
        click.echo(f"  {emoji} {level.upper()}: {count}")

    # Commands/operations
    operations = Counter(e.get("operation") for e in entries if e.get("operation"))
    if operations:
        click.echo("\n🎯 Top 10 commands:")
        for op, count in operations.most_common(10):
            click.echo(f"  • {op}: {count}")

    # Errors
    errors = [e for e in entries if e.get("level") in ("error", "critical")]
    if errors:
        click.echo(f"\n❌ Recent errors ({len(errors)} total):")
        for entry in errors[-5:]:
            ts = format_timestamp(entry.get("timestamp", ""))
            op = entry.get("operation", "unknown")
            error_type = entry.get("error_type", "Error")
            msg = entry.get("error_message", entry.get("event", ""))
            click.echo(f"  [{ts}] {op}: {error_type} - {msg[:80]}")

    # Slow operations
    slow_ops = [e for e in entries if e.get("duration_ms", 0) > 500]
    if slow_ops:
        click.echo("\n🐌 Slow operations (>500ms):")
        sorted_slow = sorted(
            slow_ops, key=lambda x: x.get("duration_ms", 0), reverse=True
        )
        for entry in sorted_slow[:5]:
            op = entry.get("operation", "unknown")
            duration = entry.get("duration_ms", 0)
            click.echo(f"  • {op}: {duration:.2f}ms")

    # Success rate
    operations_with_status = [e for e in entries if "success" in e]
    if operations_with_status:
        total = len(operations_with_status)
        successful = sum(1 for e in operations_with_status if e.get("success"))
        success_rate = (successful / total) * 100
        click.echo(f"\n✅ Success rate: {success_rate:.1f}% ({successful}/{total})")


def display_errors(entries: list[dict[str, Any]]):
    """Display detailed error information."""
    click.echo("\n" + "=" * 80)
    click.echo("❌ ERROR REPORT")
    click.echo("=" * 80)

    # Group by error type
    errors_by_type = defaultdict(list)
    for entry in entries:
        error_type = entry.get("error_type", "Unknown")
        errors_by_type[error_type].append(entry)

    click.echo("\n📊 Errors by type:")
    for error_type, error_list in sorted(
        errors_by_type.items(), key=lambda x: len(x[1]), reverse=True
    ):
        click.echo(f"\n  {error_type} ({len(error_list)} occurrences):")
        for entry in error_list[:3]:  # Show first 3 of each type
            ts = format_timestamp(entry.get("timestamp", ""))
            op = entry.get("operation", "unknown")
            msg = entry.get("error_message", entry.get("event", ""))
            cid = entry.get("correlation_id", "N/A")[:8]
            click.echo(f"    [{ts}] {op} (ID: {cid})")
            click.echo(f"      {msg}")


def display_slow_operations(entries: list[dict[str, Any]], threshold: int):
    """Display slow operation details."""
    click.echo("\n" + "=" * 80)
    click.echo(f"🐌 SLOW OPERATIONS (>{threshold}ms)")
    click.echo("=" * 80)

    sorted_ops = sorted(entries, key=lambda x: x.get("duration_ms", 0), reverse=True)

    for entry in sorted_ops[:20]:  # Top 20
        ts = format_timestamp(entry.get("timestamp", ""))
        op = entry.get("operation", "unknown")
        duration = entry.get("duration_ms", 0)
        success = "✅" if entry.get("success") else "❌"
        cid = entry.get("correlation_id", "N/A")[:8]

        click.echo(f"\n  {success} {op} - {duration:.2f}ms")
        click.echo(f"     Time: {ts} | ID: {cid}")


def display_correlation_trace(entries: list[dict[str, Any]]):
    """Display all log entries for a correlation ID."""
    click.echo("\n" + "=" * 80)
    click.echo("🔍 CORRELATION TRACE")
    click.echo("=" * 80)

    if not entries:
        click.echo("\n⚠️  No entries found for this correlation ID")
        return

    sorted_entries = sorted(entries, key=lambda x: x.get("timestamp", ""))

    for entry in sorted_entries:
        ts = format_timestamp(entry.get("timestamp", ""))
        level = entry.get("level", "info").upper()
        event = entry.get("event", "")
        op = entry.get("operation", "")

        level_emoji = {
            "DEBUG": "🐛",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🔥",
        }.get(level, "•")

        click.echo(f"\n{level_emoji} [{ts}] {level}")
        click.echo(f"   Event: {event}")
        if op:
            click.echo(f"   Operation: {op}")
        if "duration_ms" in entry:
            click.echo(f"   Duration: {entry['duration_ms']:.2f}ms")
        if "error_message" in entry:
            click.echo(f"   Error: {entry['error_message']}")


if __name__ == "__main__":
    analyze_logs()
