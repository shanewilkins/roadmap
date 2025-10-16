"""
Project management CLI commands.
"""

import click
from rich.console import Console
import os
from typing import Optional

# Initialize console for rich output with test mode detection
is_testing = "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("NO_COLOR") == "1"
console = Console(force_terminal=not is_testing, no_color=is_testing)

import click
from rich.console import Console

console = Console()

@click.group()
def project():
    """Manage projects (top-level planning documents)."""
    pass

# Basic project commands - full implementation would be extracted from main CLI
@project.command("list")
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
@click.pass_context
def list_projects(ctx: click.Context, status: Optional[str], owner: Optional[str], priority: Optional[str]):
    """List all projects with optional filtering."""
    core = ctx.obj["core"]
    
    try:
        projects_dir = core.roadmap_dir / "projects"
        
        if not projects_dir.exists():
            console.print("No projects found. Create one with 'roadmap project create'", style="yellow")
            return
            
        # Get all project files
        project_files = list(projects_dir.glob("*.md"))
        
        if not project_files:
            console.print("No projects found. Create one with 'roadmap project create'", style="yellow")
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
                            
                        projects.append({
                            "id": metadata.get("id", "unknown"),
                            "name": metadata.get("name", "Unnamed"),
                            "status": metadata.get("status", "unknown"),
                            "priority": metadata.get("priority", "medium"),
                            "owner": metadata.get("owner", "Unassigned"),
                            "file": file_path.name
                        })
            except Exception as e:
                console.print(f"⚠️  Error reading {file_path.name}: {e}", style="yellow")
                continue
        
        if not projects:
            console.print("No projects match the specified filters.", style="yellow")
            return
        
        # Display projects in a table
        from rich.table import Table
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
                project["owner"]
            )
        
        console.print(table)
        console.print(f"\nFound {len(projects)} project(s)")
        
    except Exception as e:
        console.print(f"❌ Failed to list projects: {e}", style="bold red")

@project.command("create")
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
@click.pass_context
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
):
    """Create a new project."""
    core = ctx.obj["core"]
    
    try:
        from datetime import datetime
        import uuid
        from pathlib import Path
        
        # Generate project ID
        project_id = str(uuid.uuid4())[:8]
        
        # Parse dates
        parsed_start_date = None
        parsed_target_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
            except ValueError:
                console.print("❌ Invalid start date format. Use YYYY-MM-DD", style="bold red")
                return
                
        if target_end_date:
            try:
                parsed_target_end_date = datetime.strptime(target_end_date, "%Y-%m-%d").isoformat()
            except ValueError:
                console.print("❌ Invalid target end date format. Use YYYY-MM-DD", style="bold red")
                return
        
        # Create projects directory if it doesn't exist
        projects_dir = core.roadmap_dir / "projects"
        projects_dir.mkdir(exist_ok=True)
        
        # Load and process template
        template_path = core.templates_dir / "project.md"
        if not template_path.exists():
            console.print("❌ Project template not found. Run 'roadmap init' first.", style="bold red")
            return
            
        template_content = template_path.read_text()
        
        # Replace template variables
        current_time = datetime.now().isoformat()
        
        # Convert milestones tuple to list for template
        milestone_list = list(milestones) if milestones else ["milestone_1", "milestone_2"]
        
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
        project_content = project_content.replace('priority: "medium"', f'priority: "{priority}"')
        
        # Handle status replacement
        project_content = project_content.replace('**Status:** {{ status }}', f'**Status:** planning')
        
        # Update content to use "project" terminology
        project_content = project_content.replace("# roadmap_project", f"# {name}")
        project_content = project_content.replace("Project description", description)
        
        # Handle milestone list in YAML
        if milestones:
            milestone_yaml = "\n".join([f'  - "{milestone}"' for milestone in milestones])
            project_content = project_content.replace(
                'milestones:\n  - "{{ milestone_1}}"\n  - "{{ milestone_2}}"',
                f"milestones:\n{milestone_yaml}"
            )
        
        # Save project file
        project_filename = f"{project_id}-{name.lower().replace(' ', '-')}.md"
        project_path = projects_dir / project_filename
        
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
        console.print(f"❌ Failed to create project: {e}", style="bold red")


@project.command("delete")
@click.argument("project_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_project(ctx: click.Context, project_id: str, confirm: bool):
    """Delete a project."""
    core = ctx.obj["core"]
    
    try:
        projects_dir = core.roadmap_dir / "projects"
        
        # Find project file
        project_file = None
        for file_path in projects_dir.glob("*.md"):
            if file_path.name.startswith(project_id):
                project_file = file_path
                break
        
        if not project_file:
            console.print(f"❌ Project {project_id} not found", style="bold red")
            return
        
        # Get project name for confirmation
        content = project_file.read_text()
        project_name = "unknown"
        if content.startswith("---"):
            yaml_end = content.find("---", 3)
            if yaml_end != -1:
                import yaml
                yaml_content = content[3:yaml_end]
                metadata = yaml.safe_load(yaml_content)
                project_name = metadata.get("name", "unknown")
        
        # Confirmation
        if not confirm:
            response = click.confirm(f"Are you sure you want to delete project '{project_name}' ({project_id})?")
            if not response:
                console.print("Deletion cancelled.", style="yellow")
                return
        
        # Delete file
        project_file.unlink()
        console.print(f"✅ Deleted project: {project_name} ({project_id})", style="bold green")
        
    except Exception as e:
        console.print(f"❌ Failed to delete project: {e}", style="bold red")