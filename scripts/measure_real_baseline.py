"""Use the profiler directly. This is removed - use baseline_profiler.py instead.

The profiler infrastructure in roadmap/common/profiling.py was built for this.
It measures actual function execution time without external overhead.

To establish baseline:
  poetry run python scripts/baseline_profiler.py

To compare after optimizations:
  poetry run python scripts/compare_baseline.py --baseline baseline_profile.json --current new_profile.json
"""

import click


@click.command()
def main():
    """This script was redundant. Use baseline_profiler.py instead."""
    click.secho("This script is deprecated.", fg="yellow")
    click.echo("The profiler infrastructure already does what we need.")
    click.echo()
    click.echo("Use instead:")
    click.echo("  poetry run python scripts/baseline_profiler.py")
    click.echo()
    click.echo("The profiler measures actual function performance directly,")
    click.echo("without subprocess/CLI overhead - exactly what we want.")


if __name__ == "__main__":
    main()
