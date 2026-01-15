"""Adapter implementations of core persistence interfaces."""

from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.git_history import (
    get_file_at_timestamp as _get_file_at_timestamp,
)
from roadmap.adapters.persistence.parser.issue import IssueParser
from roadmap.core.interfaces.persistence import (
    IssueParserInterface,
    PersistenceInterface,
)


class GitPersistenceAdapter(PersistenceInterface):
    """Adapter for git-based persistence operations."""

    def __init__(self, repo_path: Path | None = None):
        """Initialize with optional repo path."""
        self.repo_path = repo_path or Path.cwd()

    def get_file_at_timestamp(self, file_path: str, timestamp: datetime) -> str:
        """Get file content at a specific git timestamp.

        Args:
            file_path: Path to file relative to repo root
            timestamp: Datetime to retrieve file at

        Returns:
            File content as string

        Raises:
            FileNotFound: If file doesn't exist at timestamp
            GitHistoryError: If git operation fails
        """
        return _get_file_at_timestamp(file_path, timestamp)

    def list_files_in_directory(self, directory: str) -> list[str]:
        """List all files in a directory at HEAD."""
        from pathlib import Path as PathlibPath

        target_dir = PathlibPath(directory)
        if not target_dir.exists():
            return []

        return [
            f.name for f in target_dir.iterdir() if f.is_file() and f.suffix == ".md"
        ]


class IssueParserAdapter(IssueParserInterface):
    """Adapter for issue file parsing operations."""

    def __init__(self):
        """Initialize parser adapter."""
        pass

    def parse_issue(self, file_path: Path) -> dict[str, Any]:
        """Parse issue from YAML file.

        Args:
            file_path: Path to issue file

        Returns:
            Parsed issue data as dictionary
        """
        issue = IssueParser.parse_issue_file(file_path)
        return {
            "id": issue.id,
            "title": issue.title,
            "status": issue.status.value
            if hasattr(issue.status, "value")
            else issue.status,
            "assignee": issue.assignee,
            "milestone": issue.milestone,
            "priority": issue.priority.value
            if hasattr(issue.priority, "value")
            else issue.priority,
            "labels": issue.labels or [],
        }

    def parse_issue_content(self, content: str) -> dict[str, Any]:
        """Parse issue from string content.

        Args:
            content: File content as string

        Returns:
            Parsed issue data as dictionary
        """
        from roadmap.adapters.persistence.parser.frontmatter import FrontmatterParser

        frontmatter, text = FrontmatterParser.parse_content(content)
        return {
            "id": frontmatter.get("id"),
            "title": frontmatter.get("title"),
            "status": frontmatter.get("status"),
            "assignee": frontmatter.get("assignee"),
            "milestone": frontmatter.get("milestone"),
            "priority": frontmatter.get("priority"),
            "labels": frontmatter.get("labels", []),
        }
