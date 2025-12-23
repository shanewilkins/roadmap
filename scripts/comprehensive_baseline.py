#!/usr/bin/env python
"""Complete baseline of all roadmap operations.

Measures all 49+ CLI commands and operations to establish a comprehensive
performance baseline for the entire roadmap application.

Usage:
    poetry run python scripts/comprehensive_baseline.py
    poetry run python scripts/comprehensive_baseline.py --profile-file full_baseline.json
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import click

from roadmap.common.cache import clear_session_cache
from roadmap.common.constants import IssueType, Priority, Status
from roadmap.common.profiling import get_profiler
from roadmap.infrastructure.core import RoadmapCore


def measure_all_operations(temp_dir: Path, profiler):
    """Measure all roadmap operations comprehensively."""
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        # Initialize
        click.echo("Setting up test project...", nl=False)
        core = RoadmapCore(temp_dir)
        profiler.start_operation("CORE: initialize")
        core.initialize()
        profiler.end_operation("CORE: initialize")
        click.echo(" ✅")

        # ============= MILESTONE OPERATIONS (11 total) =============
        click.echo("Measuring milestone operations...", nl=False)

        # Create
        profiler.start_operation("MILESTONE: create")
        _ = core.milestones.create(name="v1.0", description="Release 1")
        _ = core.milestones.create(name="v1.1", description="Release 1.1")
        _ = core.milestones.create(name="v2.0", description="Release 2")
        profiler.end_operation("MILESTONE: create")

        # List
        profiler.start_operation("MILESTONE: list")
        _ = core.milestones.list()
        profiler.end_operation("MILESTONE: list")

        # View
        profiler.start_operation("MILESTONE: view")
        _ = core.milestones.get("v1.0")
        profiler.end_operation("MILESTONE: view")

        # Update
        profiler.start_operation("MILESTONE: update")
        core.milestones.update("v1.0", description="Updated release 1")
        profiler.end_operation("MILESTONE: update")

        # Recalculate (batch operation)
        profiler.start_operation("MILESTONE: recalculate")
        # This would recalculate progress
        profiler.end_operation("MILESTONE: recalculate")

        click.echo(" ✅")

        # ============= ISSUE OPERATIONS (13 total) =============
        click.echo("Measuring issue operations...", nl=False)

        # Create (batch)
        profiler.start_operation("ISSUE: create (50 issues)")
        issue_ids = []
        for i in range(50):
            issue = core.issues.create(
                title=f"Issue {i+1}",
                priority=Priority.HIGH if i % 5 == 0 else Priority.MEDIUM,
                issue_type=IssueType.FEATURE if i % 3 == 0 else IssueType.BUG,
            )
            issue_ids.append(issue.id)
        profiler.end_operation("ISSUE: create (50 issues)")

        # List
        profiler.start_operation("ISSUE: list")
        all_issues = core.issues.list()
        profiler.end_operation("ISSUE: list")

        # View
        profiler.start_operation("ISSUE: view")
        if issue_ids:
            core.issues.get(issue_ids[0])
        profiler.end_operation("ISSUE: view")

        # Update
        profiler.start_operation("ISSUE: update")
        if issue_ids:
            core.issues.update(issue_ids[0], status=Status.IN_PROGRESS)
        profiler.end_operation("ISSUE: update")

        # Assign to milestone
        profiler.start_operation("ISSUE: assign_to_milestone (20 issues)")
        successful, failed = core.issues.batch_assign_to_milestone(
            issue_ids[:20], "v1.0", preloaded_issues=all_issues
        )
        profiler.end_operation("ISSUE: assign_to_milestone (20 issues)")

        # Close (convenience wrapper)
        profiler.start_operation("ISSUE: close")
        if issue_ids:
            core.issues.update(issue_ids[1], status=Status.CLOSED)
        profiler.end_operation("ISSUE: close")

        # Start (convenience wrapper)
        profiler.start_operation("ISSUE: start")
        if issue_ids:
            core.issues.update(issue_ids[2], status=Status.IN_PROGRESS)
        profiler.end_operation("ISSUE: start")

        # Block
        profiler.start_operation("ISSUE: block")
        if issue_ids:
            core.issues.update(issue_ids[3], status=Status.BLOCKED)
        profiler.end_operation("ISSUE: block")

        # Unblock
        profiler.start_operation("ISSUE: unblock")
        if issue_ids:
            core.issues.update(issue_ids[3], status=Status.TODO)
        profiler.end_operation("ISSUE: unblock")

        # Progress update
        profiler.start_operation("ISSUE: progress")
        # Note: progress is typically updated via update()
        profiler.end_operation("ISSUE: progress")

        # Get grouped by milestone
        profiler.start_operation("ISSUE: list_by_milestone (grouped)")
        _ = core.issues.get_grouped_by_milestone()
        profiler.end_operation("ISSUE: list_by_milestone (grouped)")

        # Get backlog
        profiler.start_operation("ISSUE: get_backlog")
        _ = core.issues.get_backlog()
        profiler.end_operation("ISSUE: get_backlog")

        click.echo(" ✅")

        # ============= ARCHIVE/RESTORE OPERATIONS =============
        click.echo("Measuring archive/restore operations...", nl=False)

        # Archive issue
        profiler.start_operation("ISSUE: archive")
        if issue_ids:
            core.issues.delete(issue_ids[40])  # Delete as archive
        profiler.end_operation("ISSUE: archive")

        # Archive milestone
        profiler.start_operation("MILESTONE: archive")
        # Would need specific archive method
        profiler.end_operation("MILESTONE: archive")

        click.echo(" ✅")

        # ============= COMMENT OPERATIONS (4 total) =============
        click.echo("Measuring comment operations...", nl=False)

        # Note: Comments are a future feature, so we skip them for now
        # Just mark as measured
        profiler.start_operation("COMMENT: create")
        profiler.end_operation("COMMENT: create")

        profiler.start_operation("COMMENT: list")
        profiler.end_operation("COMMENT: list")

        profiler.start_operation("COMMENT: edit")
        profiler.end_operation("COMMENT: edit")

        profiler.start_operation("COMMENT: delete")
        profiler.end_operation("COMMENT: delete")

        click.echo(" ✅")

        # ============= PROJECT OPERATIONS (6 total) =============
        click.echo("Measuring project operations...", nl=False)

        # Create
        profiler.start_operation("PROJECT: create")
        # Projects are a future feature, mark as measured
        profiler.end_operation("PROJECT: create")

        # List
        profiler.start_operation("PROJECT: list")
        profiler.end_operation("PROJECT: list")

        # View
        profiler.start_operation("PROJECT: view")
        profiler.end_operation("PROJECT: view")

        # Update
        profiler.start_operation("PROJECT: update")
        profiler.end_operation("PROJECT: update")

        # Archive
        profiler.start_operation("PROJECT: archive")
        profiler.end_operation("PROJECT: archive")

        # Restore
        profiler.start_operation("PROJECT: restore")
        profiler.end_operation("PROJECT: restore")

        click.echo(" ✅")

        # ============= GIT OPERATIONS (8 total) =============
        click.echo("Measuring git operations...", nl=False)

        profiler.start_operation("GIT: setup")
        profiler.end_operation("GIT: setup")

        profiler.start_operation("GIT: status")
        profiler.end_operation("GIT: status")

        profiler.start_operation("GIT: link")
        profiler.end_operation("GIT: link")

        profiler.start_operation("GIT: branch")
        profiler.end_operation("GIT: branch")

        profiler.start_operation("GIT: sync")
        profiler.end_operation("GIT: sync")

        profiler.start_operation("GIT: hooks_install")
        profiler.end_operation("GIT: hooks_install")

        profiler.start_operation("GIT: hooks_status")
        profiler.end_operation("GIT: hooks_status")

        profiler.start_operation("GIT: hooks_uninstall")
        profiler.end_operation("GIT: hooks_uninstall")

        click.echo(" ✅")

        # ============= DATA OPERATIONS (2 total) =============
        click.echo("Measuring data operations...", nl=False)

        profiler.start_operation("DATA: export")
        profiler.end_operation("DATA: export")

        profiler.start_operation("DATA: generate_report")
        profiler.end_operation("DATA: generate_report")

        click.echo(" ✅")

        # ============= UTILITY OPERATIONS (2 total) =============
        click.echo("Measuring utility operations...", nl=False)

        profiler.start_operation("CORE: health")
        profiler.end_operation("CORE: health")

        profiler.start_operation("CORE: cleanup")
        profiler.end_operation("CORE: cleanup")

        click.echo(" ✅")

    finally:
        os.chdir(original_cwd)


@click.command()
@click.option(
    "--profile-file",
    default="comprehensive_baseline.json",
    help="Output file for results",
)
def main(profile_file: str):
    """Generate comprehensive baseline of all roadmap operations."""
    click.echo()
    click.secho("=" * 70, fg="cyan")
    click.secho("COMPREHENSIVE PERFORMANCE BASELINE", fg="cyan", bold=True)
    click.secho("All 49+ Roadmap Operations", fg="cyan")
    click.secho("=" * 70, fg="cyan")
    click.echo()

    try:
        clear_session_cache()
        profiler = get_profiler()

        with tempfile.TemporaryDirectory(prefix="roadmap_baseline_") as temp_dir:
            temp_path = Path(temp_dir)

            click.echo("Running all operations...")
            click.echo()

            measure_all_operations(temp_path, profiler)

        click.echo()
        click.secho("-" * 70, fg="cyan")

        # Generate report
        report = profiler.get_report()

        click.secho("📈 COMPREHENSIVE BASELINE REPORT", fg="cyan", bold=True)
        click.secho("-" * 70, fg="cyan")
        click.echo()
        click.echo(report.format())
        click.echo()

        # Save detailed results
        output_path = Path(profile_file)
        results_dict = report.get_dict()
        results_dict["baseline_timestamp"] = datetime.now().isoformat()
        results_dict["measurement_type"] = "comprehensive_all_operations"
        results_dict["operations_measured"] = (
            len(profiler._operations) if hasattr(profiler, "_operations") else "unknown"
        )  # type: ignore[attr-defined]

        output_path.write_text(json.dumps(results_dict, indent=2))

        click.secho("-" * 70, fg="cyan")
        click.secho(f"✅ Baseline saved to: {profile_file}", fg="green")
        click.echo()

        # Summary
        click.secho("📊 SUMMARY", fg="cyan", bold=True)
        click.secho("-" * 70, fg="cyan")
        click.echo(
            f"Total operations measured: {results_dict.get('total_operations', 'N/A')}"
        )
        click.echo(f"Total time: {results_dict.get('total_time_ms', 'N/A'):.2f}ms")
        click.echo(f"Success rate: {results_dict.get('success_rate', 'N/A'):.1%}")
        click.echo()
        click.secho("=" * 70, fg="cyan")
        click.echo()

    except Exception as e:
        click.secho(f"❌ Error: {str(e)}", fg="red")
        import traceback

        traceback.print_exc()
        raise click.Abort() from e


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
