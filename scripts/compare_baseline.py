"""Performance baseline comparison tool.

Compare current profiler results against the established baseline to measure
performance improvements or regressions.

Usage:
    poetry run python scripts/compare_baseline.py
    poetry run python scripts/compare_baseline.py --baseline baseline_profile.json --current profile.json
"""

import json
from pathlib import Path
from typing import Any

import click


def load_profile(file_path: str) -> dict[str, Any]:
    """Load a profile from JSON file.
    
    Args:
        file_path: Path to the profile JSON file
        
    Returns:
        Profile dictionary
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile file not found: {file_path}")
    
    return json.loads(path.read_text())


def calculate_improvement(baseline: float, current: float) -> tuple[float, str]:
    """Calculate improvement percentage.
    
    Args:
        baseline: Baseline measurement (ms)
        current: Current measurement (ms)
        
    Returns:
        Tuple of (improvement_percent, direction)
    """
    if baseline == 0:
        return 0.0, "n/a"
    
    improvement = ((baseline - current) / baseline) * 100
    
    if improvement > 0:
        direction = "⬇️ FASTER"
    elif improvement < 0:
        direction = "⬆️ SLOWER"
    else:
        direction = "→ SAME"
    
    return improvement, direction


@click.command()
@click.option(
    "--baseline",
    default="baseline_profile.json",
    help="Baseline profile file",
)
@click.option(
    "--current",
    default="baseline_profile.json",
    help="Current profile file to compare",
)
def compare_baseline(baseline: str, current: str):
    """Compare current performance against baseline.
    
    Measures improvements or regressions in operation performance.
    """
    try:
        baseline_data = load_profile(baseline)
        current_data = load_profile(current)
    except FileNotFoundError as e:
        click.secho(f"❌ Error: {str(e)}", fg="red")
        return
    
    click.echo()
    click.secho("=" * 80, fg="cyan")
    click.secho("PERFORMANCE COMPARISON REPORT", fg="cyan", bold=True)
    click.secho("=" * 80, fg="cyan")
    click.echo()
    
    # Overall metrics
    click.secho("📊 OVERALL METRICS", fg="cyan", bold=True)
    click.secho("-" * 80, fg="cyan")
    
    baseline_total = baseline_data.get("total_time_ms", 0)
    current_total = current_data.get("total_time_ms", 0)
    improvement, direction = calculate_improvement(baseline_total, current_total)
    
    click.echo(f"  Baseline Total Time:   {baseline_total:10.2f}ms")
    click.echo(f"  Current Total Time:    {current_total:10.2f}ms")
    click.echo(f"  Overall Change:        {improvement:+7.2f}% {direction}")
    click.echo()
    
    baseline_rate = baseline_data.get("success_rate", 0)
    current_rate = current_data.get("success_rate", 0)
    
    click.echo(f"  Baseline Success Rate: {baseline_rate:7.1%}")
    click.echo(f"  Current Success Rate:  {current_rate:7.1%}")
    click.echo()
    
    # Operation-by-operation comparison
    click.secho("⚡ OPERATION BREAKDOWN", fg="cyan", bold=True)
    click.secho("-" * 80, fg="cyan")
    
    baseline_ops = baseline_data.get("operations", {})
    current_ops = current_data.get("operations", {})
    
    # Get all operation names
    all_ops = set(baseline_ops.keys()) | set(current_ops.keys())
    
    # Calculate improvements for each operation
    improvements = []
    for op_name in sorted(all_ops):
        baseline_op = baseline_ops.get(op_name, {})
        current_op = current_ops.get(op_name, {})
        
        baseline_avg = baseline_op.get("avg_ms", 0)
        current_avg = current_op.get("avg_ms", 0)
        
        improvement_pct, direction = calculate_improvement(baseline_avg, current_avg)
        
        improvements.append({
            "name": op_name,
            "baseline": baseline_avg,
            "current": current_avg,
            "improvement": improvement_pct,
            "direction": direction,
        })
    
    # Sort by improvement (best first)
    improvements.sort(key=lambda x: x["improvement"], reverse=True)
    
    # Display in colored table
    for item in improvements:
        if item["baseline"] == 0 and item["current"] == 0:
            continue
        
        if item["improvement"] > 10:
            fg = "green"
            icon = "✅"
        elif item["improvement"] > 0:
            fg = "green"
            icon = "📈"
        elif item["improvement"] > -10:
            fg = "yellow"
            icon = "📉"
        else:
            fg = "red"
            icon = "❌"
        
        line = (
            f"{icon} {item['name']:30} "
            f"Baseline: {item['baseline']:8.2f}ms  "
            f"Current: {item['current']:8.2f}ms  "
            f"{item['improvement']:+7.2f}%"
        )
        click.secho(line, fg=fg)
    
    click.echo()
    
    # Summary
    click.secho("-" * 80, fg="cyan")
    click.secho("📈 SUMMARY", fg="cyan", bold=True)
    click.secho("-" * 80, fg="cyan")
    
    positive_improvements = [i for i in improvements if i["improvement"] > 0]
    negative_improvements = [i for i in improvements if i["improvement"] < 0]
    
    click.echo(f"  Operations faster:    {len(positive_improvements)}")
    click.echo(f"  Operations slower:    {len(negative_improvements)}")
    click.echo(f"  Total operations:     {len(improvements)}")
    click.echo()
    
    if positive_improvements:
        avg_gain = sum(i["improvement"] for i in positive_improvements) / len(positive_improvements)
        click.secho(f"  Average improvement:  {avg_gain:+.2f}%", fg="green")
    
    if negative_improvements:
        avg_loss = sum(i["improvement"] for i in negative_improvements) / len(negative_improvements)
        click.secho(f"  Average regression:   {avg_loss:+.2f}%", fg="red")
    
    click.echo()
    
    # Recommendation
    click.secho("-" * 80, fg="cyan")
    if improvement > 20:
        click.secho("🎉 EXCELLENT improvement! Consider deploying these changes.", fg="green", bold=True)
    elif improvement > 10:
        click.secho("✅ Good improvement! Ready to deploy.", fg="green", bold=True)
    elif improvement > 0:
        click.secho("📈 Slight improvement. Consider for next release.", fg="blue", bold=True)
    elif improvement > -5:
        click.secho("→ Negligible change. Monitor in production.", fg="yellow", bold=True)
    else:
        click.secho("❌ Performance regression detected. Investigate before deploying.", fg="red", bold=True)
    
    click.echo()
    click.secho("=" * 80, fg="cyan")
    click.echo()


if __name__ == "__main__":
    compare_baseline()
