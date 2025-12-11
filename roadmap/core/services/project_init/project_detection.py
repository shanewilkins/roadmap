"""Project detection utilities.

Shared utilities for detecting and parsing existing projects from files.
"""

from pathlib import Path
from roadmap.infrastructure.persistence.parser import ProjectParser


def detect_existing_projects(projects_dir: Path) -> list[dict]:
    """Detect existing projects in the projects directory.

    Args:
        projects_dir: Path to the projects directory

    Returns:
        List of project info dicts with name, id, and file
    """
    existing_projects = []

    if not projects_dir.exists():
        return existing_projects

    for project_file in projects_dir.glob("*.md"):
        try:
            project = ProjectParser.parse_project_file(project_file)
            existing_projects.append(
                {
                    "name": project.name,
                    "id": project.id,
                    "file": project_file.name,
                }
            )
        except Exception:
            # Skip files that don't parse as valid projects
            pass

    return existing_projects
