"""Gateway to coordination infrastructure adapter access for core services.

This module mediates all core service access to infrastructure coordination
implementations, ensuring proper layer separation between Core and Infrastructure.

All imports from roadmap.adapters accessed via coordination are localized here.
Core services use this gateway instead of importing coordination modules directly
or accessing adapters through coordination.
"""

from pathlib import Path
from typing import Any


class CoordinationGateway:
    """Gateway for infrastructure coordination operations.

    Provides a centralized interface for core services to access coordination
    functionality that internally uses adapters (git, persistence, etc.)
    without direct adapter imports in core.
    """

    @staticmethod
    def get_git_integration(repo_path: Path | None = None, config: Any = None) -> Any:
        """Get GitIntegration adapter for git operations.

        Args:
            repo_path: Path to git repository
            config: Configuration object

        Returns:
            GitIntegration instance from adapters
        """
        from roadmap.adapters.git.git import GitIntegration

        return GitIntegration(repo_path=repo_path, config=config)

    @staticmethod
    def get_state_manager(db_path: Path | str | None = None) -> Any:
        """Get StateManager for database operations.

        Args:
            db_path: Path to database file (optional)

        Returns:
            StateManager instance from adapters
        """
        from roadmap.adapters.persistence.storage import StateManager

        if db_path:
            return StateManager(db_path)
        return StateManager()

    @staticmethod
    def get_yaml_issue_repository(
        db: Any | None = None, issues_dir: Path | None = None
    ) -> Any:
        """Get YAML repository for issue persistence.

        Args:
            db: Database instance
            issues_dir: Path to issues directory

        Returns:
            YAMLIssueRepository instance from adapters
        """
        from roadmap.adapters.persistence.yaml_repositories import (
            YAMLIssueRepository,
        )

        # Both parameters are required
        if db is None or issues_dir is None:
            raise ValueError("Both 'db' and 'issues_dir' are required parameters")
        return YAMLIssueRepository(db, issues_dir)

    @staticmethod
    def get_git_sync_monitor(
        repo_path: Path | None = None, state_manager: Any = None
    ) -> Any:
        """Get GitSyncMonitor for git sync tracking.

        Args:
            repo_path: Path to git repository
            state_manager: State manager instance

        Returns:
            GitSyncMonitor instance from adapters
        """
        from roadmap.adapters.git.sync_monitor import GitSyncMonitor

        return GitSyncMonitor(repo_path=repo_path, state_manager=state_manager)

    @staticmethod
    def get_git_hook_manager(core: Any) -> Any:
        """Get GitHookManager for git hook operations.

        Args:
            core: RoadmapCore instance (required)

        Returns:
            GitHookManager instance from adapters
        """
        from roadmap.adapters.git.git_hooks import GitHookManager

        return GitHookManager(core)

    @staticmethod
    def parse_issue(file_path: Any) -> Any:
        """Parse issue from file.

        Args:
            file_path: Path to issue file

        Returns:
            Parsed Issue object
        """
        from roadmap.adapters.persistence.parser import IssueParser

        return IssueParser.parse_issue_file(file_path)

    @staticmethod
    def parse_milestone(file_path: Any) -> Any:
        """Parse milestone from file.

        Args:
            file_path: Path to milestone file

        Returns:
            Parsed Milestone object
        """
        from roadmap.adapters.persistence.parser import MilestoneParser

        return MilestoneParser.parse_milestone_file(file_path)

    @staticmethod
    def get_yaml_repositories_manager() -> Any:
        """Get combined repositories manager for multi-repo operations.

        Returns:
            Dictionary of repository classes available
        """
        from roadmap.adapters.persistence.yaml_repositories import (
            YAMLIssueRepository,
            YAMLMilestoneRepository,
            YAMLProjectRepository,
        )

        return {
            "issue": YAMLIssueRepository,
            "milestone": YAMLMilestoneRepository,
            "project": YAMLProjectRepository,
        }
