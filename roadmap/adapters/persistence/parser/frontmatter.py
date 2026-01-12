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
            loaded = yaml.safe_load(frontmatter_str)
            frontmatter = loaded if isinstance(loaded, dict) else {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

        return frontmatter, markdown_content.strip()

    @classmethod
    def serialize_file(
        cls, frontmatter: dict[str, Any], content: str, file_path: Path
    ) -> None:
        """Write frontmatter and content to a markdown file."""
        from roadmap.common.logging import get_logger, get_stack_trace

        logger = get_logger(__name__)

        logger.debug(
            "serializing_file",
            file_path=str(file_path),
            stack=get_stack_trace(depth=3),
        )

        ensure_directory_exists(file_path.parent)

        # Convert datetime objects to ISO format strings
        serializable_frontmatter = cls._prepare_frontmatter_for_yaml(frontmatter)

        frontmatter_str = yaml.dump(
            serializable_frontmatter, default_flow_style=False, sort_keys=False
        )

        # Strip trailing whitespace from frontmatter to prevent ruff errors
        frontmatter_str_stripped = frontmatter_str.rstrip() if frontmatter_str else ""

        # Ensure content doesn't have trailing whitespace
        content_stripped = content.rstrip()

        full_content = f"---\n{frontmatter_str_stripped}\n---\n\n{content_stripped}\n"

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

    @classmethod
    def extract_sync_metadata(
        cls, frontmatter: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract sync_metadata from frontmatter if present.

        Args:
            frontmatter: Parsed frontmatter dictionary

        Returns:
            Sync metadata dictionary or None if not present
        """
        return frontmatter.get("sync_metadata")

    @classmethod
    def update_sync_metadata(
        cls, frontmatter: dict[str, Any], sync_metadata: dict[str, Any] | None
    ) -> None:
        """Update sync_metadata in frontmatter.

        Args:
            frontmatter: Frontmatter dictionary to update in-place
            sync_metadata: Sync metadata to set (converts datetime to ISO strings), or None to remove
        """
        if sync_metadata:
            # Prepare nested sync_metadata for YAML serialization
            prepared = {}
            for key, value in sync_metadata.items():
                if isinstance(value, datetime):
                    prepared[key] = value.isoformat()
                elif isinstance(value, dict):
                    # Handle nested dictionaries (e.g., remote_state)
                    prepared[key] = cls._prepare_dict_for_yaml(value)
                elif hasattr(value, "value"):  # Handle enum values
                    prepared[key] = value.value
                else:
                    prepared[key] = value
            frontmatter["sync_metadata"] = prepared
        elif "sync_metadata" in frontmatter:
            # Remove if None
            del frontmatter["sync_metadata"]

    @classmethod
    def _prepare_dict_for_yaml(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively prepare a dictionary for YAML serialization."""
        prepared = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                prepared[key] = value.isoformat()
            elif isinstance(value, dict):
                prepared[key] = cls._prepare_dict_for_yaml(value)
            elif hasattr(value, "value"):  # Handle enum values
                prepared[key] = value.value
            else:
                prepared[key] = value
        return prepared
