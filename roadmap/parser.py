"""Parser for roadmap markdown files with YAML frontmatter."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from .models import Issue, IssueType, Milestone, MilestoneStatus, Priority, Status
from .persistence import YAMLValidationError, enhanced_persistence


class FrontmatterParser:
    """Parser for markdown files with YAML frontmatter."""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

    @classmethod
    def parse_file(cls, file_path: Path) -> Tuple[Dict[str, Any], str]:
        """Parse a markdown file and return frontmatter and content."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return cls.parse_content(content)

    @classmethod
    def parse_content(cls, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse markdown content and return frontmatter and body."""
        match = cls.FRONTMATTER_PATTERN.match(content)

        if not match:
            # No frontmatter found, return empty dict and full content
            return {}, content

        frontmatter_str, markdown_content = match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}")

        return frontmatter, markdown_content.strip()

    @classmethod
    def serialize_file(
        cls, frontmatter: Dict[str, Any], content: str, file_path: Path
    ) -> None:
        """Write frontmatter and content to a markdown file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert datetime objects to ISO format strings
        serializable_frontmatter = cls._prepare_frontmatter_for_yaml(frontmatter)

        frontmatter_str = yaml.dump(
            serializable_frontmatter, default_flow_style=False, sort_keys=False
        )

        full_content = f"---\n{frontmatter_str}---\n\n{content}"

        file_path.write_text(full_content, encoding="utf-8")

    @classmethod
    def _prepare_frontmatter_for_yaml(
        cls, frontmatter: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            frontmatter["created"] = datetime.fromisoformat(frontmatter["created"])
        if "updated" in frontmatter and isinstance(frontmatter["updated"], str):
            frontmatter["updated"] = datetime.fromisoformat(frontmatter["updated"])
        if "actual_start_date" in frontmatter and isinstance(
            frontmatter["actual_start_date"], str
        ):
            frontmatter["actual_start_date"] = datetime.fromisoformat(
                frontmatter["actual_start_date"]
            )
        if "actual_end_date" in frontmatter and isinstance(
            frontmatter["actual_end_date"], str
        ):
            frontmatter["actual_end_date"] = datetime.fromisoformat(
                frontmatter["actual_end_date"]
            )
        if "handoff_date" in frontmatter and isinstance(
            frontmatter["handoff_date"], str
        ):
            frontmatter["handoff_date"] = datetime.fromisoformat(
                frontmatter["handoff_date"]
            )

        # Convert string enums back to enum objects
        if "priority" in frontmatter:
            frontmatter["priority"] = Priority(frontmatter["priority"])
        if "status" in frontmatter:
            frontmatter["status"] = Status(frontmatter["status"])
        if "issue_type" in frontmatter:
            frontmatter["issue_type"] = IssueType(frontmatter["issue_type"])

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
    ) -> Tuple[bool, Optional[Issue], Optional[str]]:
        """Safely parse an issue file with enhanced validation and recovery.

        Returns:
            (success, issue, error_message)
        """
        is_valid, result = enhanced_persistence.safe_load_with_validation(
            file_path, "issue"
        )

        if not is_valid:
            return False, None, result

        try:
            # Convert the validated data to an Issue
            data = result

            # Handle datetime fields - set defaults if None
            now = datetime.now()
            created = cls._parse_datetime(data.get("created")) or now
            updated = cls._parse_datetime(data.get("updated")) or now
            due_date = cls._parse_datetime(data.get("due_date"))

            issue = Issue(
                id=data.get("id"),
                title=data.get("title"),
                description=data.get("description", ""),
                priority=Priority(data.get("priority")),
                status=Status(data.get("status")),
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
            return False, None, f"Error creating Issue object: {e}"

    @classmethod
    def save_issue_file_safe(cls, issue: Issue, file_path: Path) -> Tuple[bool, str]:
        """Safely save an issue file with automatic backup."""
        return enhanced_persistence.safe_save_with_backup(issue, file_path)

    @classmethod
    def _parse_datetime(cls, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


class MilestoneParser:
    """Parser specifically for milestone markdown files."""

    @classmethod
    def parse_milestone_file(cls, file_path: Path) -> Milestone:
        """Parse a milestone markdown file and return a Milestone object."""
        frontmatter, content = FrontmatterParser.parse_file(file_path)

        # Convert string dates back to datetime objects
        for date_field in ["created", "updated", "due_date"]:
            if date_field in frontmatter and isinstance(frontmatter[date_field], str):
                frontmatter[date_field] = datetime.fromisoformat(
                    frontmatter[date_field]
                )

        # Convert string enums back to enum objects
        if "status" in frontmatter:
            frontmatter["status"] = MilestoneStatus(frontmatter["status"])

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
    ) -> Tuple[bool, Optional[Milestone], Optional[str]]:
        """Safely parse a milestone file with enhanced validation and recovery.

        Returns:
            (success, milestone, error_message)
        """
        is_valid, result = enhanced_persistence.safe_load_with_validation(
            file_path, "milestone"
        )

        if not is_valid:
            return False, None, result

        try:
            # Convert the validated data to a Milestone
            data = result

            # Handle datetime fields - set defaults if None
            now = datetime.now()
            created = cls._parse_datetime(data.get("created")) or now
            updated = cls._parse_datetime(data.get("updated")) or now
            due_date = cls._parse_datetime(data.get("due_date"))

            milestone = Milestone(
                name=data.get("name"),
                description=data.get("description", ""),
                status=MilestoneStatus(data.get("status")),
                created=created,
                updated=updated,
                due_date=due_date,
                content=data.get("content", ""),
            )
            return True, milestone, None
        except Exception as e:
            return False, None, f"Error creating Milestone object: {e}"

    @classmethod
    def save_milestone_file_safe(
        cls, milestone: Milestone, file_path: Path
    ) -> Tuple[bool, str]:
        """Safely save a milestone file with automatic backup."""
        return enhanced_persistence.safe_save_with_backup(milestone, file_path)

    @classmethod
    def _parse_datetime(cls, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
