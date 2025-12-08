"""Parser for project markdown files."""

from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.common.datetime_parser import parse_datetime
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain import Priority, Project, ProjectStatus

from .frontmatter import FrontmatterParser


class ProjectParser:
    """Parser for project markdown files."""

    @classmethod
    def parse_project_file(cls, file_path: Path) -> Project:
        """Parse a project file and return a Project instance."""
        frontmatter, content = FrontmatterParser.parse_file(file_path)

        # Convert frontmatter to Project model
        project = Project(
            id=frontmatter.get("id", ""),
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
            status=ProjectStatus(frontmatter.get("status", "planning")),
            priority=Priority(frontmatter.get("priority", "medium")),
            owner=frontmatter.get("owner"),
            start_date=cls._parse_datetime(frontmatter.get("start_date")),
            target_end_date=cls._parse_datetime(frontmatter.get("target_end_date")),
            actual_end_date=cls._parse_datetime(frontmatter.get("actual_end_date")),
            created=cls._parse_datetime(frontmatter.get("created")) or now_utc(),
            updated=cls._parse_datetime(frontmatter.get("updated")) or now_utc(),
            milestones=frontmatter.get("milestones", []),
            estimated_hours=frontmatter.get("estimated_hours"),
            actual_hours=frontmatter.get("actual_hours"),
            content=content,
            calculated_progress=frontmatter.get("calculated_progress"),
            last_progress_update=cls._parse_datetime(
                frontmatter.get("last_progress_update")
            ),
            projected_end_date=cls._parse_datetime(
                frontmatter.get("projected_end_date")
            ),
            schedule_variance=frontmatter.get("schedule_variance"),
            completion_velocity=frontmatter.get("completion_velocity"),
            risk_level=frontmatter.get("risk_level", "low"),
        )

        return project

    @classmethod
    def save_project_file(cls, project: Project, file_path: Path) -> None:
        """Save a project to a markdown file."""
        # Create frontmatter from project data
        frontmatter = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value,
            "priority": project.priority.value,
            "owner": project.owner,
            "start_date": project.start_date.isoformat()
            if project.start_date
            else None,
            "target_end_date": project.target_end_date.isoformat()
            if project.target_end_date
            else None,
            "actual_end_date": project.actual_end_date.isoformat()
            if project.actual_end_date
            else None,
            "created": project.created.isoformat(),
            "updated": project.updated.isoformat(),
            "milestones": project.milestones,
            "estimated_hours": project.estimated_hours,
            "actual_hours": project.actual_hours,
            "calculated_progress": project.calculated_progress,
            "last_progress_update": project.last_progress_update.isoformat()
            if project.last_progress_update
            else None,
            "projected_end_date": project.projected_end_date.isoformat()
            if project.projected_end_date
            else None,
            "schedule_variance": project.schedule_variance,
            "completion_velocity": project.completion_velocity,
            "risk_level": project.risk_level.value,
        }

        # Remove None values
        frontmatter = {k: v for k, v in frontmatter.items() if v is not None}

        FrontmatterParser.serialize_file(frontmatter, project.content, file_path)

    @classmethod
    def _parse_datetime(cls, value: Any) -> datetime | None:
        """Parse datetime from various formats with timezone awareness."""
        return parse_datetime(value, source_type="file", assumed_timezone="UTC")
