"""Persistence Gateway - Mediates Core services' access to persistence adapters.

This gateway abstracts away direct imports from roadmap.adapters.persistence,
allowing Core services to request persistence operations without violating
layer boundaries.

The gateway provides:
- YAML file parsing (issues, milestones, projects)
- File persistence (save operations)
- Storage access (StateManager for database-level operations)

All imports from roadmap.adapters.persistence are localized to this module.
"""

from pathlib import Path
from typing import Any

from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project


class PersistenceGateway:
    """Mediates Core layer access to persistence adapters."""

    @staticmethod
    def parse_issue_file(file_path: Path) -> Issue:
        """Parse an issue YAML file and return Issue domain object.

        Args:
            file_path: Path to the issue YAML file.

        Returns:
            Parsed Issue domain object.
        """
        from roadmap.adapters.persistence.parser.issue import IssueParser

        return IssueParser.parse_issue_file(file_path)

    @staticmethod
    def save_issue_file(issue: Issue, file_path: Path) -> None:
        """Save an Issue domain object to YAML file.

        Args:
            issue: Issue domain object to save.
            file_path: Path to save the issue YAML file.
        """
        from roadmap.adapters.persistence.parser.issue import IssueParser

        IssueParser.save_issue_file(issue, file_path)

    @staticmethod
    def load_sync_metadata(file_path: Path) -> dict | None:
        """Load sync metadata from issue file.

        Args:
            file_path: Path to the issue YAML file.

        Returns:
            Dictionary of sync metadata or None if not present.
        """
        from roadmap.adapters.persistence.parser.issue import IssueParser

        return IssueParser.load_sync_metadata(file_path)

    @staticmethod
    def update_issue_sync_metadata(file_path: Path, sync_metadata: dict) -> None:
        """Update sync metadata in issue file.

        Args:
            file_path: Path to the issue YAML file.
            sync_metadata: Dictionary of sync metadata to update.
        """
        from roadmap.adapters.persistence.parser.issue import IssueParser

        IssueParser.update_issue_sync_metadata(file_path, sync_metadata)

    @staticmethod
    def parse_milestone_file(file_path: Path) -> Milestone:
        """Parse a milestone YAML file and return Milestone domain object.

        Args:
            file_path: Path to the milestone YAML file.

        Returns:
            Parsed Milestone domain object.
        """
        from roadmap.adapters.persistence.parser import MilestoneParser

        return MilestoneParser.parse_milestone_file(file_path)

    @staticmethod
    def save_milestone_file(milestone: Milestone, file_path: Path) -> None:
        """Save a Milestone domain object to YAML file.

        Args:
            milestone: Milestone domain object to save.
            file_path: Path to save the milestone YAML file.
        """
        from roadmap.adapters.persistence.parser import MilestoneParser

        return MilestoneParser.save_milestone_file(milestone, file_path)

    @staticmethod
    def parse_project_file(file_path: Path) -> Project:
        """Parse a project YAML file and return Project domain object.

        Args:
            file_path: Path to the project YAML file.

        Returns:
            Parsed Project domain object.
        """
        from roadmap.adapters.persistence.parser import ProjectParser

        return ProjectParser.parse_project_file(file_path)

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from content.

        Args:
            content: Raw content with frontmatter.

        Returns:
            Tuple of (frontmatter dict, remaining content).
        """
        from roadmap.adapters.persistence.parser.frontmatter import (
            FrontmatterParser,
        )

        return FrontmatterParser.parse_content(content)

    @staticmethod
    def get_state_manager() -> Any:
        """Get the StateManager for database-level operations.

        Returns:
            StateManager instance from persistence adapter.
        """
        from roadmap.adapters.persistence.storage import StateManager
        from roadmap.common.utils.path_utils import build_roadmap_paths

        db_dir = build_roadmap_paths(Path.cwd())["db_dir"]
        db_path = db_dir / "state.db"

        return StateManager(db_path=db_path)

    @staticmethod
    def get_changed_files_since_commit(ref: str = "HEAD~1", cwd: str = ".") -> set[str]:
        """Get files changed since a git reference.

        Args:
            ref: Git reference (commit, branch, tag).
            cwd: Working directory for git commands.

        Returns:
            Set of file paths that changed.
        """
        from roadmap.adapters.persistence.git_history import (
            get_changed_files_since_commit,
        )

        return get_changed_files_since_commit(ref, cwd)
