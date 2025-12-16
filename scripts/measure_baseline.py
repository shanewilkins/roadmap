"""Performance baseline measurement script.

Run this script to establish baseline metrics for current CLI performance.
Results can be compared against future optimizations to measure improvement.

Usage:
    poetry run python scripts/measure_baseline.py
    poetry run python scripts/measure_baseline.py --operations list,sync,create
    poetry run python scripts/measure_baseline.py --iterations 5
"""

import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

import click


class BaselineCollector:
    """Collect performance baseline measurements."""

    def __init__(self, iterations: int = 3):
        """Initialize collector.

        Args:
            iterations: Number of times to run each operation
        """
        self.iterations = iterations
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "iterations": iterations,
            "measurements": {},
        }

    def run_command(self, command: list[str], description: str) -> float:
        """Run a command and measure execution time.

        Args:
            command: Command to run (e.g., ['poetry', 'run', 'roadmap', 'list', 'issues'])
            description: Human-readable description

        Returns:
            Average execution time in milliseconds
        """
        times = []

        for i in range(self.iterations):
            try:
                start = time.perf_counter()
                result = subprocess.run(
                    command,
                    capture_output=True,
                    timeout=60,
                    text=True,
                )
                duration = (time.perf_counter() - start) * 1000

                if result.returncode != 0:
                    click.secho(
                        f"  ⚠️  Iteration {i+1} failed: {result.stderr[:100]}",
                        fg="yellow",
                    )
                else:
                    times.append(duration)

            except subprocess.TimeoutExpired:
                click.secho(
                    f"  ⚠️  Iteration {i+1} timeout (60s)",
                    fg="yellow",
                )
            except Exception as e:
                click.secho(f"  ⚠️  Iteration {i+1} error: {str(e)}", fg="yellow")

        if not times:
            click.secho(f"  ❌ No successful runs", fg="red")
            return 0.0

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        # Store results
        self.results["measurements"][description] = {
            "runs": len(times),
            "avg_ms": round(avg_time, 2),
            "min_ms": round(min_time, 2),
            "max_ms": round(max_time, 2),
            "total_ms": round(sum(times), 2),
            "times": [round(t, 2) for t in times],
        }

        return avg_time

    def print_result(self, description: str, avg_time_ms: float) -> None:
        """Print formatted result.

        Args:
            description: Operation description
            avg_time_ms: Average time in milliseconds
        """
        if avg_time_ms == 0.0:
            return

        if avg_time_ms < 500:
            fg = "green"
            icon = "⚡"
        elif avg_time_ms < 1000:
            fg = "yellow"
            icon = "⏱️"
        else:
            fg = "red"
            icon = "🐢"

        click.secho(
            f"  {icon} {avg_time_ms:8.2f}ms  {description}",
            fg=fg,
        )

    def save_results(self, output_file: str = "baseline_measurements.json") -> None:
        """Save results to JSON file.

        Args:
            output_file: Path to save results
        """
        output_path = Path(output_file)
        output_path.write_text(json.dumps(self.results, indent=2))
        click.secho(f"✅ Results saved to {output_file}", fg="green")


@click.command()
@click.option(
    "--iterations",
    default=3,
    help="Number of iterations per operation (default: 3)",
    type=int,
)
@click.option(
    "--operations",
    default="list,view,create,sync",
    help="Comma-separated list of operations to measure",
)
@click.option(
    "--output",
    default="baseline_measurements.json",
    help="Output file for results",
)
@click.option(
    "--save",
    is_flag=True,
    help="Save results to JSON file",
)
def measure_baseline(iterations: int, operations: str, output: str, save: bool):
    """Measure current CLI performance baseline.

    This script runs common CLI operations multiple times and measures
    execution time to establish a baseline for performance comparisons.

    Results are useful for measuring improvements after optimizations.
    """
    collector = BaselineCollector(iterations=iterations)
    ops = [op.strip() for op in operations.split(",")]

    click.echo()
    click.secho("=" * 70, fg="cyan")
    click.secho("ROADMAP CLI PERFORMANCE BASELINE", fg="cyan", bold=True)
    click.secho("=" * 70, fg="cyan")
    click.echo()

    # List of operations to benchmark
    benchmarks = {
        "list": {
            "cmd": ["poetry", "run", "roadmap", "list", "issues"],
            "desc": "List all issues",
        },
        "view": {
            "cmd": ["poetry", "run", "roadmap", "list", "issues", "--limit", "1"],
            "desc": "View single issue (with limit)",
        },
        "create": {
            "cmd": [
                "poetry",
                "run",
                "roadmap",
                "issue",
                "view",
                "--help",
            ],  # Lightweight alternative
            "desc": "Show help (lightweight command)",
        },
        "sync": {
            "cmd": ["poetry", "run", "roadmap", "--help"],
            "desc": "Show main help (lightweight command)",
        },
        "config": {
            "cmd": ["poetry", "run", "roadmap", "--version"],
            "desc": "Check version (CLI startup test)",
        },
    }

    # Filter to requested operations
    selected = {k: v for k, v in benchmarks.items() if k in ops}

    if not selected:
        click.secho(
            f"❌ No valid operations selected. Available: {', '.join(benchmarks.keys())}",
            fg="red",
        )
        return

    total_start = time.perf_counter()

    for op_key, op_info in selected.items():
        click.echo(f"📊 Measuring: {op_info['desc']}")
        click.echo(f"   Command: {' '.join(op_info['cmd'])}")
        click.echo(f"   Running {iterations} iterations...")

        avg_time = collector.run_command(op_info["cmd"], op_info["desc"])
        collector.print_result(op_info["desc"], avg_time)
        click.echo()

    total_time = (time.perf_counter() - total_start) * 1000

    # Summary
    click.secho("-" * 70, fg="cyan")
    click.secho("📈 SUMMARY", fg="cyan", bold=True)
    click.secho("-" * 70, fg="cyan")

    for desc, data in collector.results["measurements"].items():
        click.echo(f"  {desc:40} {data['avg_ms']:8.2f}ms avg")

    click.echo()
    click.secho(f"Total measurement time: {total_time:.2f}ms", fg="blue")
    click.secho(f"Timestamp: {collector.results['timestamp']}", fg="blue")
    click.echo()

    if save:
        collector.save_results(output)

    click.secho("=" * 70, fg="cyan")
    click.echo()

    # Save results even if not explicitly requested
    collector.save_results(output)


if __name__ == "__main__":
    measure_baseline()
