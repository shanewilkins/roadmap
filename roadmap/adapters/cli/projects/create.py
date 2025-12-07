"""Create project command."""

from datetime import datetime

import click

from roadmap.common.console import get_console
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_file_operation,
    verbose_output,
)

# Initialize console
console = get_console()


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

        # Parse dates
        parsed_start_date = None
        parsed_target_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.strptime(
                    start_date, "%Y-%m-%d"
                ).isoformat()
            except ValueError:
                console.print(
                    "❌ Invalid start date format. Use YYYY-MM-DD", style="bold red"
                )
                return

        if target_end_date:
            try:
                parsed_target_end_date = datetime.strptime(
                    target_end_date, "%Y-%m-%d"
                ).isoformat()
            except ValueError:
                console.print(
                    "❌ Invalid target end date format. Use YYYY-MM-DD",
                    style="bold red",
                )
                return

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

        # Replace template variables
        current_time = datetime.now().isoformat()

        # Convert milestones tuple to list for template
        milestone_list = (
            list(milestones) if milestones else ["milestone_1", "milestone_2"]
        )

        replacements = {
            "{{ project_id }}": project_id,
            "{{ project_name }}": name,
            "{{ project_description }}": description,
            "{{ project_owner }}": owner or "",
            "{{ start_date }}": parsed_start_date or "",
            "{{ target_end_date }}": parsed_target_end_date or "",
            "{{ created_date }}": current_time,
            "{{ updated_date }}": current_time,
            "{{ estimated_hours }}": str(estimated_hours) if estimated_hours else "0",
            "{{ milestone_1 }}": milestone_list[0] if len(milestone_list) > 0 else "",
            "{{ milestone_2 }}": milestone_list[1] if len(milestone_list) > 1 else "",
        }

        project_content = template_content
        for placeholder, value in replacements.items():
            project_content = project_content.replace(placeholder, value)

        # Handle priority replacement
        project_content = project_content.replace(
            'priority: "medium"', f'priority: "{priority}"'
        )

        # Handle status replacement
        project_content = project_content.replace(
            "**Status:** {{ status }}", "**Status:** planning"
        )

        # Update content to use "project" terminology
        project_content = project_content.replace("# roadmap_project", f"# {name}")
        project_content = project_content.replace("Project description", description)

        # Handle milestone list in YAML
        if milestones:
            milestone_yaml = "\n".join(
                [f'  - "{milestone}"' for milestone in milestones]
            )
            project_content = project_content.replace(
                'milestones:\n  - "{{ milestone_1}}"\n  - "{{ milestone_2}}"',
                f"milestones:\n{milestone_yaml}",
            )

        # Save project file
        project_filename = f"{project_id}-{name.lower().replace(' ', '-')}.md"
        project_path = projects_dir / project_filename

        with track_file_operation("write", str(project_path)):
            with open(project_path, "w") as f:
                f.write(project_content)

        console.print("✅ Created project:", style="bold green")
        console.print(f"   ID: {project_id}")
        console.print(f"   Name: {name}")
        console.print(f"   Priority: {priority}")
        if owner:
            console.print(f"   Owner: {owner}")
        if estimated_hours:
            console.print(f"   Estimated: {estimated_hours}h")
        console.print(f"   File: {project_path.relative_to(core.root_path)}")

    except Exception as e:
        log_error_with_context(
            e,
            operation="project_create",
            entity_type="project",
            additional_context={"name": name},
        )
        console.print(f"❌ Failed to create project: {e}", style="bold red")
