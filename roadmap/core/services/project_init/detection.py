"""Service for detecting and analyzing existing projects."""

from pathlib import Path

from roadmap.infrastructure.persistence_gateway import PersistenceGateway


class ProjectDetectionService:
    """Service for detecting and analyzing existing projects."""

    @staticmethod
    def detect_existing_projects(projects_dir: Path) -> list[dict]:
        """Detect existing projects in the projects directory.

        Args:
            projects_dir: Path to the projects directory

        Returns:
            List of dicts with 'name', 'id', and 'file' for each existing project
        """
        existing_projects = []

        if not projects_dir.exists():
            return existing_projects

        for project_file in projects_dir.glob("*.md"):
            try:
                project = PersistenceGateway.parse_project_file(project_file)
                existing_projects.append(
                    {
                        "name": project.name,
                        "id": project.id,
                        "file": project_file.name,
                    }
                )
            except Exception:
                # Skip projects that can't be parsed
                continue

        return existing_projects
