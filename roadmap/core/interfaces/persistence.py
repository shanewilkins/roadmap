"""Persistence interface for core services.

Defines contract for file persistence and git history operations.
"""

from abc import ABC, abstractmethod
from datetime import datetime


class FileNotFound(Exception):
    """Raised when a file is not found in history."""

    pass


class GitHistoryError(Exception):
    """Raised when git history operations fail."""

    pass


class PersistenceInterface(ABC):
    """Interface for file persistence operations."""

    @abstractmethod
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
        pass

    @abstractmethod
    def list_files_in_directory(self, directory: str) -> list[str]:
        """List all files in a directory at HEAD."""
        pass
