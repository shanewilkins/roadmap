"""Parser for issue markdown files."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.common.datetime_parser import parse_datetime
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain import Issue, IssueType, Priority, Status

from ..persistence import enhanced_persistence
from .frontmatter import FrontmatterParser


class IssueParser:
    """Parser specifically for issue markdown files."""

    @staticmethod
    def _parse_datetime_field(frontmatter: dict, field_name: str) -> None:
        """Parse a datetime field in frontmatter if present and string."""
        if field_name in frontmatter and isinstance(frontmatter[field_name], str):
            frontmatter[field_name] = parse_datetime(frontmatter[field_name], "file")

    @staticmethod
    def _parse_enum_field(
        frontmatter: dict, field_name: str, enum_class, file_path: Path
    ) -> None:
        """Parse enum field with validation."""
        if field_name not in frontmatter:
            return

        try:
            frontmatter[field_name] = enum_class(frontmatter[field_name])
        except ValueError as e:
            valid_values = [v.value for v in enum_class]
            raise ValueError(
                f"Invalid {field_name} '{frontmatter[field_name]}' in {file_path}. "
                f"Valid values are: {', '.join(valid_values)}"
            ) from e

    @staticmethod
    def _ensure_list_fields(frontmatter: dict) -> None:
        """Ensure dependency fields are lists."""
        if "depends_on" not in frontmatter:
            frontmatter["depends_on"] = []
        if "blocks" not in frontmatter:
            frontmatter["blocks"] = []

    @classmethod
    def parse_issue_file(cls, file_path: Path) -> Issue:
        """Parse an issue markdown file and return an Issue object."""
        frontmatter, content = FrontmatterParser.parse_file(file_path)

        # Parse date fields
        cls._parse_datetime_field(frontmatter, "created")
        cls._parse_datetime_field(frontmatter, "updated")
        cls._parse_datetime_field(frontmatter, "actual_start_date")
        cls._parse_datetime_field(frontmatter, "actual_end_date")
        cls._parse_datetime_field(frontmatter, "handoff_date")

        # Parse enum fields with validation
        cls._parse_enum_field(frontmatter, "priority", Priority, file_path)
        cls._parse_enum_field(frontmatter, "status", Status, file_path)
        cls._parse_enum_field(frontmatter, "issue_type", IssueType, file_path)

        # Ensure list fields exist
        cls._ensure_list_fields(frontmatter)

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
