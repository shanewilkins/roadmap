"""Parser interfaces for domain object deserialization.

These interfaces define contracts for parsing files and content into domain objects.
Implementations should be in the infrastructure/adapters layer.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from roadmap.core.domain import Issue, Milestone, Project


class IssueParserInterface(ABC):
    """Contract for parsing issue markdown files."""

    @abstractmethod
    def parse_issue_file(self, file_path: Path) -> "Issue":
        """Parse an issue markdown file and return an Issue domain object.

        Args:
            file_path: Path to issue markdown file

        Returns:
            Issue domain object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def parse_issue_content(self, content: str) -> dict[str, Any]:
        """Parse issue content string and return frontmatter as dict.

        Args:
            content: File content as string

        Returns:
            Parsed frontmatter as dictionary
        """
        pass


class MilestoneParserInterface(ABC):
    """Contract for parsing milestone markdown files."""

    @abstractmethod
    def parse_milestone_file(self, file_path: Path) -> "Milestone":
        """Parse a milestone markdown file and return a Milestone domain object.

        Args:
            file_path: Path to milestone markdown file

        Returns:
            Milestone domain object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def parse_milestone_content(self, content: str) -> dict[str, Any]:
        """Parse milestone content string and return frontmatter as dict.

        Args:
            content: File content as string

        Returns:
            Parsed frontmatter as dictionary
        """
        pass


class ProjectParserInterface(ABC):
    """Contract for parsing project markdown files."""

    @abstractmethod
    def parse_project_file(self, file_path: Path) -> "Project":
        """Parse a project markdown file and return a Project domain object.

        Args:
            file_path: Path to project markdown file

        Returns:
            Project domain object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def parse_project_content(self, content: str) -> dict[str, Any]:
        """Parse project content string and return frontmatter as dict.

        Args:
            content: File content as string

        Returns:
            Parsed frontmatter as dictionary
        """
        pass


class FrontmatterParserInterface(ABC):
    """Contract for parsing YAML frontmatter from markdown files."""

    @abstractmethod
    def parse_file(self, file_path: Path) -> tuple[dict[str, Any], str]:
        """Parse a markdown file and extract frontmatter and content.

        Args:
            file_path: Path to markdown file

        Returns:
            Tuple of (frontmatter dict, content string)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def parse_content(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse markdown content and extract frontmatter and text.

        Args:
            content: File content as string

        Returns:
            Tuple of (frontmatter dict, content string)
        """
        pass
