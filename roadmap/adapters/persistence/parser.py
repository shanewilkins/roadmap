"""Parser for roadmap markdown files with YAML frontmatter."""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from roadmap.common.datetime_parser import parse_datetime
from roadmap.common.file_utils import ensure_directory_exists, file_exists_check
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Project,
    ProjectStatus,
    Status,
)

from .persistence import enhanced_persistence


class FrontmatterParser:
    """Parser for markdown files with YAML frontmatter."""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

    @classmethod
    def parse_file(cls, file_path: Path) -> tuple[dict[str, Any], str]:
        """Parse a markdown file and return frontmatter and content."""
        if not file_exists_check(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return cls.parse_content(content)

    @classmethod
    def parse_content(cls, content: str) -> tuple[dict[str, Any], str]:
        """Parse markdown content and return frontmatter and body."""
        match = cls.FRONTMATTER_PATTERN.match(content)

        if not match:
            # No frontmatter found, return empty dict and full content
            return {}, content

        frontmatter_str, markdown_content = match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

        return frontmatter, markdown_content.strip()

    @classmethod
    def serialize_file(
        cls, frontmatter: dict[str, Any], content: str, file_path: Path
    ) -> None:
        """Write frontmatter and content to a markdown file."""
        ensure_directory_exists(file_path.parent)

        # Convert datetime objects to ISO format strings
        serializable_frontmatter = cls._prepare_frontmatter_for_yaml(frontmatter)

        frontmatter_str = yaml.dump(
            serializable_frontmatter, default_flow_style=False, sort_keys=False
        )

        full_content = f"---\n{frontmatter_str}---\n\n{content}"

        file_path.write_text(full_content, encoding="utf-8")

    @classmethod
    def _prepare_frontmatter_for_yaml(
        cls, frontmatter: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare frontmatter for YAML serialization."""
        prepared = {}
        for key, value in frontmatter.items():
            if isinstance(value, datetime):
                prepared[key] = value.isoformat()
            elif hasattr(value, "value"):  # Handle enum values
                prepared[key] = value.value
            elif value is None:
                prepared[key] = None
            else:
                prepared[key] = value
        return prepared


class IssueParser:
    """Parser specifically for issue markdown files."""

    @classmethod
    def parse_issue_file(cls, file_path: Path) -> Issue:
        """Parse an issue markdown file and return an Issue object."""
        frontmatter, content = FrontmatterParser.parse_file(file_path)

        # Convert string dates back to datetime objects
        if "created" in frontmatter and isinstance(frontmatter["created"], str):
            frontmatter["created"] = parse_datetime(frontmatter["created"], "file")
        if "updated" in frontmatter and isinstance(frontmatter["updated"], str):
            frontmatter["updated"] = parse_datetime(frontmatter["updated"], "file")
        if "actual_start_date" in frontmatter and isinstance(
            frontmatter["actual_start_date"], str
        ):
            frontmatter["actual_start_date"] = parse_datetime(
                frontmatter["actual_start_date"], "file"
            )
        if "actual_end_date" in frontmatter and isinstance(
            frontmatter["actual_end_date"], str
        ):
            frontmatter["actual_end_date"] = parse_datetime(
                frontmatter["actual_end_date"], "file"
            )
        if "handoff_date" in frontmatter and isinstance(
            frontmatter["handoff_date"], str
        ):
            frontmatter["handoff_date"] = parse_datetime(
                frontmatter["handoff_date"], "file"
            )

        # Convert string enums back to enum objects with validation
        if "priority" in frontmatter:
            try:
                frontmatter["priority"] = Priority(frontmatter["priority"])
            except ValueError as e:
                valid_priorities = [p.value for p in Priority]
                raise ValueError(
                    f"Invalid priority '{frontmatter['priority']}' in {file_path}. "
                    f"Valid priority values are: {', '.join(valid_priorities)}"
                ) from e
        if "status" in frontmatter:
            try:
                frontmatter["status"] = Status(frontmatter["status"])
            except ValueError as e:
                valid_statuses = [s.value for s in Status]
                raise ValueError(
                    f"Invalid status '{frontmatter['status']}' in {file_path}. "
                    f"Valid status values are: {', '.join(valid_statuses)}"
                ) from e
        if "issue_type" in frontmatter:
            try:
                frontmatter["issue_type"] = IssueType(frontmatter["issue_type"])
            except ValueError as e:
                valid_types = [t.value for t in IssueType]
                raise ValueError(
                    f"Invalid issue_type '{frontmatter['issue_type']}' in {file_path}. "
                    f"Valid type values are: {', '.join(valid_types)}"
                ) from e

        # Ensure dependencies are lists
        if "depends_on" not in frontmatter:
            frontmatter["depends_on"] = []
        if "blocks" not in frontmatter:
            frontmatter["blocks"] = []

        # Set content
        frontmatter["content"] = content

        return Issue(**frontmatter)

    @classmethod
    def save_issue_file(cls, issue: Issue, file_path: Path) -> None:
        """Save an Issue object to a markdown file."""
        frontmatter = issue.model_dump(exclude={"content"})
        FrontmatterParser.serialize_file(frontmatter, issue.content, file_path)

    @classmethod
    def parse_issue_file_safe(
        cls, file_path: Path
    ) -> tuple[bool, Issue | None, str | None]:
        """Safely parse an issue file with enhanced validation and recovery.

        Returns:
            (success, issue, error_message)
        """
        is_valid, result = enhanced_persistence.safe_load_with_validation(
            file_path, "issue"
        )

        if not is_valid:
            # result is a string error message
            return False, None, str(result)

        try:
            # Convert the validated data to an Issue
            # At this point, result must be a dict since is_valid is True
            data = result if isinstance(result, dict) else {}

            # Handle datetime fields - set defaults if None
            now = now_utc()
            created = cls._parse_datetime(data.get("created")) or now
            updated = cls._parse_datetime(data.get("updated")) or now
            due_date = cls._parse_datetime(data.get("due_date"))

            issue = Issue(
                id=data.get("id") or str(uuid.uuid4())[:8],
                title=data.get("title") or "Untitled Issue",
                priority=Priority(data.get("priority"))
                if data.get("priority")
                else Priority.MEDIUM,
                status=Status(data.get("status"))
                if data.get("status")
                else Status.TODO,
                assignee=data.get("assignee"),
                milestone=data.get("milestone"),
                labels=data.get("labels", []),
                created=created,
                updated=updated,
                due_date=due_date,
                content=data.get("content", ""),
            )
            return True, issue, None
        except ValueError as e:
            # Check if it's an enum validation error
            error_str = str(e)
            if "status" in error_str:
                valid_statuses = [s.value for s in Status]
                return (
                    False,
                    None,
                    f"Invalid status in {file_path}: {e}. Valid values: {', '.join(valid_statuses)}",
                )
            elif "priority" in error_str:
                valid_priorities = [p.value for p in Priority]
                return (
                    False,
                    None,
                    f"Invalid priority in {file_path}: {e}. Valid values: {', '.join(valid_priorities)}",
                )
            elif "issue_type" in error_str:
                valid_types = [t.value for t in IssueType]
                return (
                    False,
                    None,
                    f"Invalid issue_type in {file_path}: {e}. Valid values: {', '.join(valid_types)}",
                )
            return False, None, f"Error creating Issue object: {e}"
        except Exception as e:
            return False, None, f"Error creating Issue object: {e}"

    @classmethod
    def save_issue_file_safe(cls, issue: Issue, file_path: Path) -> tuple[bool, str]:
        """Safely save an issue file with automatic backup."""
        try:
            cls.save_issue_file(issue, file_path)
            return True, "Issue saved successfully"
        except Exception as e:
            return False, f"Error saving issue: {e}"

    @classmethod
    def _parse_datetime(cls, value: Any) -> datetime | None:
        """Parse datetime from various formats with timezone awareness."""
        return parse_datetime(value, source_type="file", assumed_timezone="UTC")


class MilestoneParser:
    """Parser specifically for milestone markdown files."""

    @classmethod
    def parse_milestone_file(cls, file_path: Path) -> Milestone:
        """Parse a milestone markdown file and return a Milestone object."""
        frontmatter, content = FrontmatterParser.parse_file(file_path)

        # Convert string dates back to datetime objects
        for date_field in ["created", "updated", "due_date"]:
            if date_field in frontmatter and isinstance(frontmatter[date_field], str):
                frontmatter[date_field] = parse_datetime(
                    frontmatter[date_field], "file"
                )

        # Convert string enums back to enum objects with validation
        if "status" in frontmatter:
            try:
                frontmatter["status"] = MilestoneStatus(frontmatter["status"])
            except ValueError as e:
                valid_statuses = [s.value for s in MilestoneStatus]
                raise ValueError(
                    f"Invalid status '{frontmatter['status']}' in {file_path}. "
                    f"Valid status values are: {', '.join(valid_statuses)}"
                ) from e

        # Set content
        frontmatter["content"] = content

        return Milestone(**frontmatter)

    @classmethod
    def save_milestone_file(cls, milestone: Milestone, file_path: Path) -> None:
        """Save a Milestone object to a markdown file."""
        frontmatter = milestone.model_dump(exclude={"content"})
        FrontmatterParser.serialize_file(frontmatter, milestone.content, file_path)

    @classmethod
    def parse_milestone_file_safe(
        cls, file_path: Path
    ) -> tuple[bool, Milestone | None, str | None]:
        """Safely parse a milestone file with enhanced validation and recovery.

        Returns:
            (success, milestone, error_message)
        """
        is_valid, result = enhanced_persistence.safe_load_with_validation(
            file_path, "milestone"
        )

        if not is_valid:
            # result is a string error message
            return False, None, str(result)

        try:
            # Convert the validated data to a Milestone
            # At this point, result must be a dict since is_valid is True
            data = result if isinstance(result, dict) else {}

            # Handle datetime fields - set defaults if None
            now = now_utc()
            created = cls._parse_datetime(data.get("created")) or now
            updated = cls._parse_datetime(data.get("updated")) or now
            due_date = cls._parse_datetime(data.get("due_date"))

            milestone = Milestone(
                name=data.get("name") or "Untitled Milestone",
                description=data.get("description", ""),
                status=MilestoneStatus(data.get("status"))
                if data.get("status")
                else MilestoneStatus.OPEN,
                created=created,
                updated=updated,
                due_date=due_date,
                content=data.get("content", ""),
            )
            return True, milestone, None
        except ValueError as e:
            # Check if it's an enum validation error
            if "status" in str(e):
                valid_statuses = [s.value for s in MilestoneStatus]
                return (
                    False,
                    None,
                    f"Invalid status in {file_path}: {e}. Valid values: {', '.join(valid_statuses)}",
                )
            return False, None, f"Error creating Milestone object: {e}"
        except Exception as e:
            return False, None, f"Error creating Milestone object: {e}"

    @classmethod
    def save_milestone_file_safe(
        cls, milestone: Milestone, file_path: Path
    ) -> tuple[bool, str]:
        """Safely save a milestone file with automatic backup."""
        try:
            cls.save_milestone_file(milestone, file_path)
            return True, "Milestone saved successfully"
        except Exception as e:
            return False, f"Error saving milestone: {e}"

    @classmethod
    def _parse_datetime(cls, value: Any) -> datetime | None:
        """Parse datetime from various formats with timezone awareness."""
        return parse_datetime(value, source_type="file", assumed_timezone="UTC")


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
