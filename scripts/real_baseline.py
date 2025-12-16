#!/usr/bin/env python
"""Real baseline using actual roadmap operations via domain coordinators.

Measures real operations using the profiler on RoadmapCore domain coordinators.

Usage:
    poetry run python scripts/real_baseline.py
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import click

from roadmap.common.profiling import get_profiler
from roadmap.common.cache import clear_session_cache
from roadmap.infrastructure.core import RoadmapCore
from roadmap.core.domain.issue import Priority, IssueType


def measure_real_operations(temp_dir: Path):
    """Measure real roadmap operations using domain coordinators."""
    profiler = get_profiler()
    
    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    try:
        # Initialize roadmap
        click.echo("Initializing roadmap...", nl=False)
        core = RoadmapCore(temp_dir)
        profiler.start_operation("initialize")
        core.initialize()
        profiler.end_operation("initialize")
        click.echo(" ✅")
        
        # Operation 1: Create milestone
        click.echo("Measuring: Create milestone...", nl=False)
        profiler.start_operation("create_milestone")
        milestone = core.milestones.create(
            name="v1.0",
            description="First release",
        )
        profiler.end_operation("create_milestone")
        click.echo(" ✅")
        
        # Operation 2: Create issues
        click.echo("Measuring: Create 5 issues...", nl=False)
        profiler.start_operation("create_issues")
        issue_ids = []
        for i in range(5):
            issue = core.issues.create(
                title=f"Issue {i+1}",
                priority=Priority.HIGH if i % 2 == 0 else Priority.MEDIUM,
                issue_type=IssueType.FEATURE,
            )
            issue_ids.append(issue.id)
        profiler.end_operation("create_issues")
        click.echo(" ✅")
        
        # Operation 3: Assign issues to milestone
        click.echo("Measuring: Assign issues to milestone...", nl=False)
        profiler.start_operation("assign_to_milestone")
        for issue_id in issue_ids[:3]:
            core.issues.assign_to_milestone(issue_id, "v1.0")
        profiler.end_operation("assign_to_milestone")
        click.echo(" ✅")
        
        # Operation 4: List all issues
        click.echo("Measuring: List all issues...", nl=False)
        profiler.start_operation("list_issues")
        all_issues = core.issues.list()
        profiler.end_operation("list_issues")
        click.echo(" ✅")
        
        # Operation 5: Get issues by milestone (grouped)
        click.echo("Measuring: Get issues grouped by milestone...", nl=False)
        profiler.start_operation("list_by_milestone")
        by_milestone = core.issues.get_grouped_by_milestone()
        profiler.end_operation("list_by_milestone")
        click.echo(" ✅")
        
        # Operation 6: Get specific issue
        if issue_ids:
            click.echo("Measuring: Get specific issue...", nl=False)
            profiler.start_operation("get_issue")
            issue = core.issues.get(issue_ids[0])
            profiler.end_operation("get_issue")
            click.echo(" ✅")
            
            # Operation 7: Update issue
            click.echo("Measuring: Update issue...", nl=False)
            profiler.start_operation("update_issue")
            core.issues.update(
                issue_ids[0],
                status="in-progress",
                priority="critical",
            )
            profiler.end_operation("update_issue")
            click.echo(" ✅")
        
        # Operation 8: List milestones
        click.echo("Measuring: List milestones...", nl=False)
        profiler.start_operation("list_milestones")
        milestones = core.milestones.list()
        profiler.end_operation("list_milestones")
        click.echo(" ✅")
        
        # Operation 9: Get specific milestone
        if milestones:
            click.echo("Measuring: Get milestone...", nl=False)
            profiler.start_operation("get_milestone")
            m = core.milestones.get("v1.0")
            profiler.end_operation("get_milestone")
            click.echo(" ✅")
    
    finally:
        os.chdir(original_cwd)


@click.command()
@click.option(
    "--profile-file",
    default="real_baseline.json",
    help="Output file for results",
)
def main(profile_file: str):
    """Generate a real performance baseline using actual operations."""
    click.echo()
    click.secho("=" * 70, fg="cyan")
    click.secho("REAL PERFORMANCE BASELINE", fg="cyan", bold=True)
    click.secho("Using Actual Roadmap Operations", fg="cyan")
    click.secho("=" * 70, fg="cyan")
    click.echo()
    
    try:
        clear_session_cache()
        profiler = get_profiler()
        
        with tempfile.TemporaryDirectory(prefix="roadmap_baseline_") as temp_dir:
            temp_path = Path(temp_dir)
            
            click.echo("Running real operations on test project...")
            click.echo()
            
            measure_real_operations(temp_path)
        
        click.echo()
        click.secho("-" * 70, fg="cyan")
        
        # Generate report
        report = profiler.get_report()
        
        click.secho("📈 BASELINE REPORT", fg="cyan", bold=True)
        click.secho("-" * 70, fg="cyan")
        click.echo()
        click.echo(report.format())
        click.echo()
        
        # Save detailed results
        output_path = Path(profile_file)
        results_dict = report.get_dict()
        results_dict["baseline_timestamp"] = datetime.now().isoformat()
        results_dict["measurement_type"] = "real_operations"
        
        output_path.write_text(json.dumps(results_dict, indent=2))
        
        click.secho("-" * 70, fg="cyan")
        click.secho(f"✅ Baseline saved to: {profile_file}", fg="green")
        click.echo()
        click.secho("=" * 70, fg="cyan")
        click.echo()
        
    except Exception as e:
        click.secho(f"❌ Error: {str(e)}", fg="red")
        import traceback
        traceback.print_exc()
        raise click.Abort() from e


if __name__ == "__main__":
    main()
