"""Project service - handles all project-related operations.

The ProjectService manages:
- Project listing and retrieval
- Project saving/persistence
- Milestone-based progress calculation
- Project completion tracking

Extracted from core.py to separate business logic.
"""

from pathlib import Path
from typing import Any

from roadmap.domain.milestone import MilestoneStatus
from roadmap.domain.project import Project
from roadmap.infrastructure.file_enumeration import FileEnumerationService
from roadmap.infrastructure.persistence.parser import MilestoneParser, ProjectParser
from roadmap.infrastructure.storage import StateManager
from roadmap.shared.timezone_utils import now_utc


class ProjectService:
    """Service for managing projects."""

    def __init__(self, db: StateManager, projects_dir: Path, milestones_dir: Path):
        """Initialize project service.

        Args:
            db: State manager for database operations
            projects_dir: Path to projects directory
            milestones_dir: Path to milestones directory (for progress calc)
        """
        self.db = db
        self.projects_dir = projects_dir
        self.milestones_dir = milestones_dir

    def list_projects(self) -> list[Project]:
        """List all projects.

        Returns:
            List of Project objects sorted by creation date
        """
        projects = FileEnumerationService.enumerate_and_parse(
            self.projects_dir,
            ProjectParser.parse_project_file,
        )

        projects.sort(key=lambda x: x.created)
        return projects

    def get_project(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project object if found, None otherwise
        """

        def id_matcher(project: Project) -> bool:
            return project.id.startswith(project_id)

        projects = FileEnumerationService.enumerate_with_filter(
            self.projects_dir,
            ProjectParser.parse_project_file,
            id_matcher,
        )

        return projects[0] if projects else None

    def save_project(self, project: Project) -> bool:
        """Save an updated project to disk.

        Args:
            project: Project object to save

        Returns:
            True if saved, False on error
        """
        # Find and update the existing project file
        for project_file in self.projects_dir.rglob("*.md"):
            try:
                test_project = ProjectParser.parse_project_file(project_file)
                if test_project.id == project.id:
                    project.updated = now_utc()
                    ProjectParser.save_project_file(project, project_file)
                    return True
            except Exception:
                continue

        # If not found, create new file
        project.updated = now_utc()
        project_path = self.projects_dir / project.filename
        ProjectParser.save_project_file(project, project_path)
        return True

    def create_project(
        self,
        name: str,
        description: str = "",
        milestones: list[str] | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            milestones: List of associated milestone names

        Returns:
            Newly created Project object
        """
        project = Project(
            name=name,
            description=description,
            milestones=milestones or [],
            content=f"# {name}\n\n## Description\n\n{description}\n\n## Overview\n\n- Status: Not Started\n- Priority: Medium",
        )

        self.save_project(project)
        return project

    def update_project(self, project_id: str, **updates) -> Project | None:
        """Update a project.

        Args:
            project_id: Project identifier
            **updates: Fields to update

        Returns:
            Updated Project object if found, None otherwise
        """
        project = self.get_project(project_id)
        if not project:
            return None

        # Update fields
        for field, value in updates.items():
            if hasattr(project, field):
                setattr(project, field, value)

        self.save_project(project)
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        for project_file in self.projects_dir.rglob("*.md"):
            try:
                project = ProjectParser.parse_project_file(project_file)
                if project.id.startswith(project_id):
                    project_file.unlink()
                    return True
            except Exception:
                continue
        return False

    def calculate_progress(self, project_id: str) -> dict[str, Any]:
        """Calculate project progress based on associated milestones.

        Returns dict with:
        - total_milestones: Total milestones in project
        - completed_milestones: Completed milestones
        - progress: Percentage complete
        - milestone_status: Status breakdown by milestone

        Args:
            project_id: Project identifier

        Returns:
            Dict with progress metrics
        """
        project = self.get_project(project_id)
        if not project:
            return {
                "total_milestones": 0,
                "completed_milestones": 0,
                "progress": 0.0,
                "milestone_status": {},
            }

        # Get milestones for this project
        milestones = FileEnumerationService.enumerate_and_parse(
            self.milestones_dir,
            MilestoneParser.parse_milestone_file,
        )

        # Build lookup for project's milestones
        milestone_statuses = {}
        completed_count = 0

        for milestone_name in project.milestones:
            for milestone in milestones:
                if milestone.name == milestone_name:
                    milestone_statuses[milestone_name] = milestone.status.value
                    if milestone.status == MilestoneStatus.CLOSED:
                        completed_count += 1
                    break

        total = len(project.milestones)
        progress = (completed_count / total * 100) if total > 0 else 0.0

        return {
            "total_milestones": total,
            "completed_milestones": completed_count,
            "progress": progress,
            "milestone_status": milestone_statuses,
        }

    def complete_project(self, project_id: str) -> Project | None:
        """Mark a project as completed.

        Args:
            project_id: Project identifier

        Returns:
            Completed Project object if found, None otherwise
        """
        from roadmap.domain.project import ProjectStatus

        return self.update_project(project_id, status=ProjectStatus.COMPLETED)
