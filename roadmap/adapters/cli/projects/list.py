"""List projects command."""

import click
from rich.table import Table

from roadmap.adapters.cli.logging_decorators import verbose_output
from roadmap.common.console import get_console

console = get_console()


@click.command("list")
@click.option(
    "--status",
    type=click.Choice(["planning", "active", "on-hold", "completed", "cancelled"]),
    help="Filter by status",
)
@click.option(
    "--owner",
    help="Filter by owner",
)
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Filter by priority",
)
@click.option(
    "--overdue", is_flag=True, help="Show only overdue projects (past target end date)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
def list_projects(
    ctx: click.Context,
    status: str | None,
    owner: str | None,
    priority: str | None,
    overdue: bool,
    verbose: bool,
):
    """List all projects with optional filtering."""
    core = ctx.obj["core"]

    try:
        projects_dir = core.roadmap_dir / "projects"

        if not projects_dir.exists():
            console.print(
                "No projects found. Create one with 'roadmap project create'",
                style="yellow",
            )
            return

        # Get all project files
        project_files = list(projects_dir.rglob("*.md"))

        if not project_files:
            console.print(
                "No projects found. Create one with 'roadmap project create'",
                style="yellow",
            )
            return

        # Parse and filter projects
        projects = []
        for file_path in project_files:
            try:
                content = file_path.read_text()
                # Extract YAML frontmatter
                if content.startswith("---"):
                    yaml_end = content.find("---", 3)
                    if yaml_end != -1:
                        import yaml

                        yaml_content = content[3:yaml_end]
                        metadata = yaml.safe_load(yaml_content)

                        # Apply filters
                        if status and metadata.get("status") != status:
                            continue
                        if owner and metadata.get("owner") != owner:
                            continue
                        if priority and metadata.get("priority") != priority:
                            continue

                        # Apply overdue filter
                        if overdue:
                            from datetime import datetime

                            target_end = metadata.get("target_end_date")
                            if target_end:
                                try:
                                    # Parse the date (handle various formats)
                                    if isinstance(target_end, str):
                                        end_date = datetime.fromisoformat(
                                            target_end.replace("Z", "+00:00")
                                        )
                                    else:
                                        end_date = target_end

                                    # Normalize timezone for comparison
                                    end_date = (
                                        end_date.replace(tzinfo=None)
                                        if end_date.tzinfo
                                        else end_date
                                    )
                                    now = datetime.now()

                                    # Skip if not overdue or already completed
                                    project_status = metadata.get("status", "")
                                    if end_date >= now or project_status in [
                                        "completed",
                                        "cancelled",
                                    ]:
                                        continue
                                except (ValueError, AttributeError):
                                    # Skip projects with invalid dates
                                    continue
                            else:
                                # Skip projects without target_end_date when filtering for overdue
                                continue

                        projects.append(
                            {
                                "id": metadata.get("id", "unknown"),
                                "name": metadata.get("name", "Unnamed"),
                                "status": metadata.get("status", "unknown"),
                                "priority": metadata.get("priority", "medium"),
                                "owner": metadata.get("owner", "Unassigned"),
                                "file": file_path.name,
                            }
                        )
            except Exception as e:
                console.print(f"⚠️  Error reading {file_path.name}: {e}", style="yellow")
                continue

        if not projects:
            console.print("No projects match the specified filters.", style="yellow")
            return

        # Display projects in a table
        table = Table(title="Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Status", style="magenta")
        table.add_column("Priority", style="yellow")
        table.add_column("Owner", style="green")

        for project in sorted(projects, key=lambda x: x["name"]):
            table.add_row(
                project["id"][:8],
                project["name"],
                project["status"],
                project["priority"],
                project["owner"],
            )

        console.print(table)
        console.print(f"\nFound {len(projects)} project(s)")

    except Exception as e:
        console.print(f"❌ Failed to list projects: {e}", style="bold red")
