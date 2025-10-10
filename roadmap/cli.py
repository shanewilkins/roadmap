"""Main CLI module for the roadmap tool."""

import click
from rich.console import Console
from rich.table import Table

from roadmap import __version__

console = Console()


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    ctx.ensure_object(dict)


@main.command()
def init() -> None:
    """Initialize a new roadmap in the current directory."""
    console.print("🗺️  Initializing new roadmap...", style="bold green")
    # TODO: Implement roadmap initialization
    console.print("✅ Roadmap initialized successfully!", style="bold green")


@main.command()
def status() -> None:
    """Show the current status of the roadmap."""
    console.print("📊 Roadmap Status", style="bold blue")
    
    # Create a sample table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Milestone", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Progress", style="yellow")
    
    table.add_row("Project Setup", "✅ Complete", "100%")
    table.add_row("Core Features", "🚧 In Progress", "60%")
    table.add_row("Documentation", "📝 Planned", "0%")
    
    console.print(table)


@main.command()
@click.argument("milestone_name")
def add(milestone_name: str) -> None:
    """Add a new milestone to the roadmap."""
    console.print(f"➕ Adding milestone: {milestone_name}", style="bold yellow")
    # TODO: Implement milestone addition
    console.print("✅ Milestone added successfully!", style="bold green")


@main.command()
@click.argument("milestone_name")
def complete(milestone_name: str) -> None:
    """Mark a milestone as complete."""
    console.print(f"✅ Marking milestone as complete: {milestone_name}", style="bold green")
    # TODO: Implement milestone completion
    console.print("🎉 Milestone completed!", style="bold green")


@main.command()
def list() -> None:
    """List all milestones in the roadmap."""
    console.print("📋 Roadmap Milestones", style="bold blue")
    # TODO: Implement milestone listing
    console.print("No milestones found. Use 'roadmap add <name>' to add one.", style="yellow")


if __name__ == "__main__":
    main()