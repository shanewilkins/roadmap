"""Parser for milestone markdown files."""

from pathlib import Path

from roadmap.common.datetime_parser import parse_datetime
from roadmap.core.domain import Milestone, MilestoneStatus

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

        # Backward-compatibility: some historical files may be missing `name`.
        # Use filename stem so list/view commands remain consistent with disk state.
        if not frontmatter.get("name"):
            frontmatter["name"] = file_path.stem

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

        # Map legacy "description" field to "content" if present
        if "description" in frontmatter and "content" not in frontmatter:
            frontmatter["content"] = frontmatter.pop("description")
        else:
            # Otherwise use the body content
            frontmatter["content"] = content

        # If headline is not provided, use first line of content as fallback
        if "headline" not in frontmatter or not frontmatter["headline"]:
            first_line = content.split("\n")[0] if content else ""
            frontmatter["headline"] = first_line[:100]  # Limit to 100 chars

        return Milestone(**frontmatter)

    @classmethod
    def save_milestone_file(cls, milestone: Milestone, file_path: Path) -> None:
        """Save a Milestone object to a markdown file."""
        frontmatter = milestone.model_dump(exclude={"content", "file_path"})
        FrontmatterParser.serialize_file(frontmatter, milestone.content, file_path)
