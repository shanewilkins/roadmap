"""List projects command."""

from datetime import UTC

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.decorators import with_output_support
from roadmap.common.console import get_console
from roadmap.common.datetime_parser import UnifiedDateTimeParser
from roadmap.common.formatters import ProjectTableFormatter
from roadmap.common.logging import verbose_output
from roadmap.common.models import ColumnType

console = get_console()


def _parse_project_metadata(file_path) -> dict | None:
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
        metadata = yaml.safe_load(yaml_content)

        # Add ID from frontmatter if present, or extract from filename
        if isinstance(metadata, dict) and not metadata.get("id"):
            # Extract ID from filename (format: {id}-{name}.md)
            filename_stem = file_path.stem
            if "-" in filename_stem:
                metadata["id"] = filename_stem.split("-", 1)[0]

        return metadata if isinstance(metadata, dict) else None
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
            end_date = UnifiedDateTimeParser.parse_iso_datetime(target_end)
            if not end_date:
                return False
        else:
            end_date = target_end

        end_date = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
        now = datetime.now(UTC)

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
@with_output_support(
    available_columns=["id", "name", "status", "priority", "owner"],
    column_types={
        "id": ColumnType.STRING,
        "name": ColumnType.STRING,
        "status": ColumnType.ENUM,
        "priority": ColumnType.ENUM,
        "owner": ColumnType.STRING,
    },
)
@verbose_output
def list_projects(
    ctx: click.Context,
    status: str | None,
    owner: str | None,
    priority: str | None,
    overdue: bool,
    verbose: bool,  # noqa: F841 - Used by @verbose_output decorator
):
    """List all projects with optional filtering.

    Supports output formatting with --format, --columns, --sort-by, --filter flags.
    """
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

        # Convert to TableData for structured output
        description = "filtered" if any([status, owner, priority, overdue]) else "all"
        table_data = ProjectTableFormatter.projects_to_table_data(
            filtered,
            title="Projects",
            description=description,
        )

        return table_data

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="list_projects",
            entity_type="project",
            entity_id="all",
            context={
                "status": status,
                "owner": owner,
                "priority": priority,
                "overdue": overdue,
            },
            fatal=True,
        )
        console.print(f"❌ Failed to list projects: {e}", style="bold red")
