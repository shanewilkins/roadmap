"""YAML file parsing for .roadmap markdown files."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class FileParser:
    """Handles parsing and hashing of markdown files with YAML frontmatter."""

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(
                "failed_to_calculate_hash",
                file_path=str(file_path),
                error=str(e),
                severity="operational",
            )
            return ""

    @staticmethod
    def parse_yaml_frontmatter(file_path: Path) -> dict[str, Any]:
        """Parse YAML frontmatter from markdown file.

        Expects format:
            ---
            key: value
            ---
            # Markdown content
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for frontmatter delimiters
            if not content.startswith("---\n"):
                return {}

            # Find the end of frontmatter
            try:
                end_marker = content.index("\n---\n", 4)
                frontmatter = content[4:end_marker]
                loaded = yaml.safe_load(frontmatter)
                return loaded if isinstance(loaded, dict) else {}
            except ValueError:
                # No end marker found, treat entire file as YAML
                loaded = yaml.safe_load(content)
                return loaded if isinstance(loaded, dict) else {}

        except Exception as e:
            logger.error(
                "failed_to_parse_yaml",
                file_path=str(file_path),
                error=str(e),
                severity="data_error",
            )
            return {}

    @staticmethod
    def extract_file_metadata(file_path: Path) -> dict[str, Any]:
        """Extract file metadata without parsing YAML.

        Returns:
            Dictionary with 'hash', 'size', and 'modified_time' keys
        """
        try:
            file_stat = file_path.stat()
            return {
                "hash": FileParser.calculate_file_hash(file_path),
                "size": file_stat.st_size,
                "modified_time": datetime.fromtimestamp(file_stat.st_mtime),
            }
        except Exception as e:
            logger.error(
                "failed_to_extract_metadata",
                file_path=str(file_path),
                error=str(e),
                severity="data_error",
            )
            return {}
