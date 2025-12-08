"""Frontmatter parser for markdown files with YAML headers."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from roadmap.common.file_utils import ensure_directory_exists, file_exists_check


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
