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
    def save_issue_file(
        cls, issue: Issue, file_path: Path, sync_metadata: dict | None = None
    ) -> None:
        """Save an Issue object to a markdown file.

        Args:
            issue: Issue object to save
            file_path: Path to write the file to
            sync_metadata: Optional sync metadata to include in frontmatter
        """
        frontmatter = issue.model_dump(exclude={"content"})

        # Add sync_metadata if provided
        if sync_metadata:
            FrontmatterParser.update_sync_metadata(frontmatter, sync_metadata)

        FrontmatterParser.serialize_file(frontmatter, issue.content, file_path)

    @classmethod
    def load_sync_metadata(cls, file_path: Path) -> dict | None:
        """Load sync_metadata from an issue file without parsing the full issue.

        Args:
            file_path: Path to the issue file

        Returns:
            Sync metadata dictionary or None if not present
        """
        frontmatter, _ = FrontmatterParser.parse_file(file_path)
        return FrontmatterParser.extract_sync_metadata(frontmatter)

    @classmethod
    def update_issue_sync_metadata(cls, file_path: Path, sync_metadata: dict) -> None:
        """Update only the sync_metadata in an issue file without parsing the full Issue.

        This is useful for updating sync state without deserializing and re-serializing
        the entire Issue object.

        Args:
            file_path: Path to the issue file
            sync_metadata: Sync metadata to set
        """
        frontmatter, content = FrontmatterParser.parse_file(file_path)
        FrontmatterParser.update_sync_metadata(frontmatter, sync_metadata)
        FrontmatterParser.serialize_file(frontmatter, content, file_path)

    @classmethod
    def _validate_enum_field(
        cls, field_name: str, value: str | None, enum_class
    ) -> tuple[bool, Any, str | None]:
        """Validate and convert enum field. Returns (success, value, error_message)."""
        if not value:
            return True, None, None

        try:
            return True, enum_class(value), None
        except ValueError:
            valid_values = [e.value for e in enum_class]
            error_msg = (
                f"Invalid {field_name}: {value}. Valid: {', '.join(valid_values)}"
            )
            return False, None, error_msg

    @classmethod
    def _extract_issue_dates(
        cls, data: dict
    ) -> tuple[datetime, datetime, datetime | None]:
        """Extract and parse date fields from data."""
        now = now_utc()
        created = cls._parse_datetime(data.get("created")) or now
        updated = cls._parse_datetime(data.get("updated")) or now
        due_date = cls._parse_datetime(data.get("due_date"))
        return created, updated, due_date

    @classmethod
    def _build_issue_from_data(
        cls, data: dict, file_path: Path
    ) -> tuple[bool, Issue | None, str | None]:
        """Build Issue object from validated data. Returns (success, issue, error_message)."""
        # Validate priority
        success, priority, error = cls._validate_enum_field(
            "priority", data.get("priority"), Priority
        )
        if not success:
            return False, None, f"{error} in {file_path}"
        priority = priority or Priority.MEDIUM

        # Validate status
        success, status, error = cls._validate_enum_field(
            "status", data.get("status"), Status
        )
        if not success:
            return False, None, f"{error} in {file_path}"
        status = status or Status.TODO

        # Validate issue_type
        success, _, error = cls._validate_enum_field(
            "issue_type", data.get("issue_type"), IssueType
        )
        if not success:
            return False, None, f"{error} in {file_path}"

        # Extract dates
        created, updated, due_date = cls._extract_issue_dates(data)

        try:
            issue = Issue(
                id=data.get("id") or str(uuid.uuid4())[:8],
                title=data.get("title") or "Untitled Issue",
                priority=priority,
                status=status,
                assignee=data.get("assignee"),
                milestone=data.get("milestone"),
                labels=data.get("labels", []),
                created=created,
                updated=updated,
                due_date=due_date,
                content=data.get("content", ""),
            )
            return True, issue, None
        except Exception as e:
            return False, None, f"Error creating Issue: {e}"

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
            return cls._build_issue_from_data(data, file_path)
        except Exception as e:
            return False, None, f"Error processing issue file: {e}"

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
