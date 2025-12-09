"""Create project command."""

from datetime import datetime

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.cli_validators import parse_iso_date
from roadmap.common.console import get_console
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.common.formatters import format_operation_failure, format_operation_success
from roadmap.infrastructure.logging import (
    log_command,
    track_file_operation,
    verbose_output,
)

# Initialize console
console = get_console()


def _validate_date_input(date_string: str, date_type: str) -> str | None:
    """Validate and parse date input, showing error on failure."""
    parsed = parse_iso_date(date_string)
    if parsed is None:
        console.print(
            f"❌ Invalid {date_type} format. Use YYYY-MM-DD",
            style="bold red",
        )
    return parsed


def _prepare_project_dates(
    start_date: str, target_end_date: str
) -> tuple[str | None, str | None] | None:
    """Parse and validate project dates. Returns tuple or None on error."""
    parsed_start_date = None
    parsed_target_end_date = None

    if start_date:
        parsed_start_date = _validate_date_input(start_date, "start date")
        if start_date and parsed_start_date is None:
            return None

    if target_end_date:
        parsed_target_end_date = _validate_date_input(
            target_end_date, "target end date"
        )
        if target_end_date and parsed_target_end_date is None:
            return None

    return (parsed_start_date, parsed_target_end_date)


def _build_template_replacements(
    project_id: str,
    name: str,
    description: str,
    owner: str,
    start_date: str | None,
    target_end_date: str | None,
    estimated_hours: float,
    milestones: list,
    current_time: str,
) -> dict:
    """Build dictionary of template variable replacements."""
    return {
        "{{ project_id }}": project_id,
        "{{ project_name }}": name,
        "{{ project_description }}": description,
        "{{ project_owner }}": owner or "",
        "{{ start_date }}": start_date or "",
        "{{ target_end_date }}": target_end_date or "",
        "{{ created_date }}": current_time,
        "{{ updated_date }}": current_time,
        "{{ estimated_hours }}": str(estimated_hours) if estimated_hours else "0",
        "{{ milestone_1 }}": milestones[0] if len(milestones) > 0 else "",
        "{{ milestone_2 }}": milestones[1] if len(milestones) > 1 else "",
    }


def _apply_template_replacements(content: str, replacements: dict) -> str:
    """Apply all template variable replacements to content."""
    result = content
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def _apply_priority_and_status(content: str, priority: str) -> str:
    """Apply priority and status replacements to content."""
    content = content.replace('priority: "medium"', f'priority: "{priority}"')
    content = content.replace("**Status:** {{ status }}", "**Status:** planning")
    return content


def _apply_project_content_updates(content: str, name: str, description: str) -> str:
    """Apply project name and description content updates."""
    content = content.replace("# roadmap_project", f"# {name}")
    content = content.replace("Project description", description)
    return content


def _apply_milestone_updates(content: str, milestones: list) -> str:
    """Apply milestone list updates to content."""
    if milestones:
        milestone_yaml = "\n".join([f'  - "{milestone}"' for milestone in milestones])
        content = content.replace(
            'milestones:\n  - "{{ milestone_1}}"\n  - "{{ milestone_2}}"',
            f"milestones:\n{milestone_yaml}",
        )
    return content


def _generate_project_content(
    template_content: str,
    project_id: str,
    name: str,
    description: str,
    owner: str,
    start_date: str | None,
    target_end_date: str | None,
    priority: str,
    estimated_hours: float,
    milestones: tuple,
) -> str:
    """Generate complete project content from template."""
    current_time = datetime.now().isoformat()
    milestone_list = list(milestones) if milestones else ["milestone_1", "milestone_2"]

    # Build and apply template replacements
    replacements = _build_template_replacements(
        project_id,
        name,
        description,
        owner,
        start_date,
        target_end_date,
        estimated_hours,
        milestone_list,
        current_time,
    )
    content = _apply_template_replacements(template_content, replacements)

    # Apply priority and status
    content = _apply_priority_and_status(content, priority)

    # Apply project content updates
    content = _apply_project_content_updates(content, name, description)

    # Apply milestone updates
    content = _apply_milestone_updates(content, milestone_list)

    return content


@click.command("create")
@click.argument("name")
@click.option(
    "--description",
    "-d",
    default="Project description",
    help="Project description",
)
@click.option(
    "--owner",
    "-o",
    help="Project owner",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Project priority",
)
@click.option(
    "--start-date",
    "-s",
    help="Project start date (YYYY-MM-DD)",
)
@click.option(
    "--target-end-date",
    "-e",
    help="Target end date (YYYY-MM-DD)",
)
@click.option(
    "--estimated-hours",
    "-h",
    type=float,
    help="Estimated hours to complete",
)
@click.option(
    "--milestones",
    "-m",
    multiple=True,
    help="Milestone names (can be specified multiple times)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
@log_command("project_create", entity_type="project", track_duration=True)
def create_project(
    ctx: click.Context,
    name: str,
    description: str,
    owner: str,
    priority: str,
    start_date: str,
    target_end_date: str,
    estimated_hours: float,
    milestones: tuple,
    verbose: bool,
):
    """Create a new project."""
    core = ctx.obj["core"]

    try:
        import uuid

        # Generate project ID
        project_id = str(uuid.uuid4())[:8]

        # Parse and validate dates
        date_result = _prepare_project_dates(start_date, target_end_date)
        if date_result is None:
            return
        parsed_start_date, parsed_target_end_date = date_result

        # Create projects directory if it doesn't exist
        projects_dir = core.roadmap_dir / "projects"
        projects_dir = ensure_directory_exists(projects_dir)

        # Load and process template
        template_path = core.templates_dir / "project.md"
        if not template_path.exists():
            console.print(
                "❌ Project template not found. Run 'roadmap init' first.",
                style="bold red",
            )
            return

        template_content = template_path.read_text()

        # Generate project content from template
        project_content = _generate_project_content(
            template_content,
            project_id,
            name,
            description,
            owner,
            parsed_start_date,
            parsed_target_end_date,
            priority,
            estimated_hours,
            milestones,
        )

        # Save project file
        project_filename = f"{project_id}-{name.lower().replace(' ', '-')}.md"
        project_path = projects_dir / project_filename

        with track_file_operation("write", str(project_path)):
            with open(project_path, "w") as f:
                f.write(project_content)

        # Format and display success message
        extra_details = {
            "Priority": priority,
            "Estimated hours": str(estimated_hours) if estimated_hours else "N/A",
            "File": str(project_path.relative_to(core.root_path)),
        }
        if owner:
            extra_details["Owner"] = owner
        lines = format_operation_success(
            "✅", "Created", name, project_id, None, extra_details
        )
        for line in lines:
            console.print(line, style="green")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="create_project",
            entity_type="project",
            entity_id="new",
            context={"name": name, "owner": owner, "target_end_date": target_end_date},
            fatal=True,
        )
        lines = format_operation_failure("Create", name, str(e))
        for line in lines:
            console.print(line, style="bold red")
