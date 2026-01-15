"""Persistence interface for core services.

Defines contract for file persistence, git history, and issue parsing.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any


class FileNotFound(Exception):
    """Raised when a file is not found in history."""

    pass


class GitHistoryError(Exception):
    """Raised when git history operations fail."""

    pass


class PersistenceInterface(ABC):
    """Interface for file persistence operations."""

    @abstractmethod
    def get_file_at_timestamp(
        self, file_path: str, timestamp: datetime
    ) -> str:
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
        pass

    @abstractmethod
    def list_files_in_directory(self, directory: str) -> list[str]:
        """List all files in a directory at HEAD."""
        pass


class IssueParserInterface(ABC):
    """Interface for parsing issue files."""

    @abstractmethod
    def parse_issue(self, file_path: Path) -> dict[str, Any]:
        """Parse issue from YAML file.

        Args:
            file_path: Path to issue file

        Returns:
            Parsed issue data as dictionary
        """
        pass

    @abstractmethod
    def parse_issue_content(self, content: str) -> dict[str, Any]:
        """Parse issue from string content.

        Args:
            content: File content as string

        Returns:
            Parsed issue data as dictionary
        """
        pass
