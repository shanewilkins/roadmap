"""Parser for milestone markdown files."""

from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.common.datetime_parser import parse_datetime
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain import Milestone, MilestoneStatus

from ..persistence import enhanced_persistence
from .frontmatter import FrontmatterParser


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
    def _build_milestone_from_data(
        cls, data: dict, file_path: Path
    ) -> tuple[bool, Milestone | None, str | None]:
        """Build Milestone object from parsed data.

        Args:
            data: Parsed milestone data
            file_path: Path to milestone file (for error reporting)

        Returns:
            (success, milestone, error_message)
        """
        try:
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

        # Convert the validated data to a Milestone
        # At this point, result must be a dict since is_valid is True
        data = result if isinstance(result, dict) else {}
        return cls._build_milestone_from_data(data, file_path)

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
