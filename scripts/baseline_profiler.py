"""Performance baseline measurement using the built-in profiler.

This script measures current CLI performance using the official profiling system.
Results are stored for comparison against future optimizations.

Usage:
    poetry run python scripts/baseline_profiler.py
    poetry run python scripts/baseline_profiler.py --profile-file baseline.json
"""

import json
from datetime import datetime
from pathlib import Path

import click

from roadmap.common.profiling import get_profiler
from roadmap.common.cache import clear_session_cache


def simulate_operations():
    """Simulate typical CLI operations to establish baseline.
    
    These represent common workflows users would run.
    
    NOTE: These are still simulated. To measure REAL operations,
    we would need to create actual roadmap projects with data.
    This baseline is useful for tracking profiler infrastructure overhead
    and relative changes, but doesn't reflect production performance yet.
    """
    profiler = get_profiler()
    
    # Simulate issue listing operation
    profiler.start_operation("list_issues_parse")
    # Simulate parsing/formatting ~500 lines
    for i in range(500):
        x = i * 2  # lightweight processing
    profiler.end_operation("list_issues_parse")
    
    # Simulate team member lookup
    profiler.start_operation("get_team_members_api")
    # Simulate API call overhead
    import time
    time.sleep(0.01)  # 10ms simulated network
    profiler.end_operation("get_team_members_api")
    
    # Simulate milestone fetching
    profiler.start_operation("get_milestones_api")
    time.sleep(0.015)  # 15ms simulated network
    profiler.end_operation("get_milestones_api")
    
    # Simulate issue detail loading
    profiler.start_operation("fetch_issue_details")
    time.sleep(0.008)  # 8ms simulated I/O
    profiler.end_operation("fetch_issue_details")
    
    # Simulate issue creation workflow
    profiler.start_operation("validate_issue_data")
    for i in range(100):
        _ = str(i)  # lightweight validation
    profiler.end_operation("validate_issue_data")
    
    # Simulate file I/O
    profiler.start_operation("read_config_file")
    time.sleep(0.005)  # 5ms simulated file I/O
    profiler.end_operation("read_config_file")
    
    # Simulate formatting output
    profiler.start_operation("format_output")
    for i in range(1000):
        _ = f"item_{i}"  # string formatting
    profiler.end_operation("format_output")
    
    # Simulate successful operation
    profiler.start_operation("sync_to_github")
    time.sleep(0.020)  # 20ms simulated network
    profiler.end_operation("sync_to_github")
    
    # Simulate an operation with error
    profiler.start_operation("fetch_with_retry")
    try:
        time.sleep(0.003)
        raise ValueError("Simulated network error")
    except Exception:
        profiler.end_operation("fetch_with_retry", error=True)


@click.command()
@click.option(
    "--profile-file",
    default="baseline_profile.json",
    help="Output file for profiler results",
)
@click.option(
    "--iterations",
    default=3,
    help="Number of times to run the simulation",
    type=int,
)
def establish_baseline(profile_file: str, iterations: int):
    """Establish performance baseline using the official profiler.
    
    This runs simulated operations and collects profiling data to create
    a baseline for measuring performance improvements.
    
    Note: These are simulated operations for now. Real baselines should
    measure actual CLI commands against real data when available.
    """
    click.echo()
    click.secho("=" * 70, fg="cyan")
    click.secho("ESTABLISHING PERFORMANCE BASELINE", fg="cyan", bold=True)
    click.secho("Using Official Profiling System", fg="cyan")
    click.secho("(With Simulated Operations)", fg="yellow")
    click.secho("=" * 70, fg="cyan")
    click.echo()
    click.secho("⚠️  WARNING: These are simulated operations, not real CLI commands", fg="yellow")
    click.secho("   Baseline is useful for tracking relative improvements.", fg="yellow")
    click.echo()
    
    profiler = get_profiler()
    
    click.echo(f"📊 Running {iterations} iterations of simulated operations...")
    click.echo()
    
    for iteration in range(iterations):
        click.echo(f"  Iteration {iteration + 1}/{iterations}...", nl=False)
        
        # Clear for fresh session
        clear_session_cache()
        profiler.clear()
        
        # Run simulated operations
        simulate_operations()
        
        click.echo(" ✅")
    
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
    results_dict["iterations_run"] = iterations
    
    output_path.write_text(json.dumps(results_dict, indent=2))
    
    click.secho("-" * 70, fg="cyan")
    click.secho(f"✅ Baseline saved to: {profile_file}", fg="green")
    click.echo()
    
    # Summary statistics
    click.secho("📊 SUMMARY", fg="cyan", bold=True)
    click.secho("-" * 70, fg="cyan")
    click.echo(f"  Total Time:        {results_dict['total_time_ms']:.2f}ms")
    click.echo(f"  Total Operations:  {results_dict['total_operations']}")
    click.echo(f"  Success Rate:      {results_dict['success_rate']:.1%}")
    
    # Find slowest operation
    slowest_op = None
    for op_name, op_data in results_dict.get('operations', {}).items():
        if slowest_op is None or op_data['total_ms'] > results_dict['operations'][slowest_op]['total_ms']:
            slowest_op = op_name
    
    if slowest_op:
        click.echo(f"  Slowest Operation: {slowest_op}")
    click.echo()
    
    click.secho("💾 Next Steps:", fg="blue")
    click.echo("  1. After optimizations, run this script again")
    click.echo("  2. Compare results to measure improvement")
    click.echo("  3. Track improvements over time")
    click.echo()
    
    click.secho("=" * 70, fg="cyan")
    click.echo()


if __name__ == "__main__":
    establish_baseline()
