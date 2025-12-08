"""List projects command."""

import click
from rich.table import Table

from roadmap.common.console import get_console
from roadmap.infrastructure.logging import verbose_output

console = get_console()


def _parse_project_metadata(file_path):
    """Parse project metadata from markdown file."""
    try:
        content = file_path.read_text()
        if not content.startswith("---"):
            return None

        yaml_end = content.find("---", 3)
        if yaml_end == -1:
            return None

        import yaml

        yaml_content = content[3:yaml_end]
        return yaml.safe_load(yaml_content)
    except Exception:
        return None


def _apply_status_filter(metadata, status):
    """Check if project matches status filter."""
    if not status:
        return True
    return metadata.get("status") == status


def _apply_owner_filter(metadata, owner):
    """Check if project matches owner filter."""
    if not owner:
        return True
    return metadata.get("owner") == owner


def _apply_priority_filter(metadata, priority):
    """Check if project matches priority filter."""
    if not priority:
        return True
    return metadata.get("priority") == priority


def _apply_overdue_filter(metadata):
    """Check if project is overdue."""
    from datetime import datetime

    target_end = metadata.get("target_end_date")
    if not target_end:
        return False

    try:
        if isinstance(target_end, str):
            end_date = datetime.fromisoformat(target_end.replace("Z", "+00:00"))
        else:
            end_date = target_end

        end_date = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
        now = datetime.now()

        project_status = metadata.get("status", "")
        if project_status in ["completed", "cancelled"]:
            return False

        return end_date < now
    except (ValueError, AttributeError):
        return False


def _filter_projects(projects, status, owner, priority, overdue):
    """Apply all filters to project list."""
    filtered = []

    for metadata in projects:
        if not _apply_status_filter(metadata, status):
            continue
        if not _apply_owner_filter(metadata, owner):
            continue
        if not _apply_priority_filter(metadata, priority):
            continue
        if overdue and not _apply_overdue_filter(metadata):
            continue

        filtered.append(metadata)

    return filtered


def _extract_project_info(metadata):
    """Extract displayable project info from metadata."""
    return {
        "id": metadata.get("id", "unknown"),
        "name": metadata.get("name", "Unnamed"),
        "status": metadata.get("status", "unknown"),
        "priority": metadata.get("priority", "medium"),
        "owner": metadata.get("owner", "Unassigned"),
    }


def _build_projects_table(projects):
    """Build Rich table from project list."""
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

    return table


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

        # Parse all projects
        project_metadatas = []
        for file_path in project_files:
            metadata = _parse_project_metadata(file_path)
            if metadata:
                project_metadatas.append(metadata)
            else:
                console.print(f"⚠️  Error reading {file_path.name}", style="yellow")

        # Apply filters
        filtered = _filter_projects(project_metadatas, status, owner, priority, overdue)

        if not filtered:
            console.print("No projects match the specified filters.", style="yellow")
            return

        # Extract display info and build table
        projects = [_extract_project_info(m) for m in filtered]
        table = _build_projects_table(projects)

        console.print(table)
        console.print(f"\nFound {len(projects)} project(s)")

    except Exception as e:
        console.print(f"❌ Failed to list projects: {e}", style="bold red")
