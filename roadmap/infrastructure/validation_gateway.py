"""Gateway to validation infrastructure adapter access for core services.

This module mediates core service access to validation-related adapters,
ensuring proper layer separation between Core and Infrastructure.

All imports from roadmap.adapters accessed via validation are localized here.
Core services use this gateway instead of importing validation modules directly
or accessing adapters through validation.
"""

from typing import Any


class ValidationGateway:
    """Gateway for validation operations.

    Provides a centralized interface for core services to access validation
    functionality that internally uses adapters (GitHub, persistence parsers, etc.)
    without direct adapter imports in core.
    """

    @staticmethod
    def get_github_client(token: str | None = None, org: str | None = None) -> Any:
        """Get GitHub API client for validation operations.

        Args:
            token: GitHub API token (optional)
            org: GitHub organization (optional)

        Returns:
            GitHub client instance from adapters
        """
        from roadmap.adapters.github.github import GitHubClient

        return GitHubClient(token=token, owner=org)

    @staticmethod
    def parse_issue_for_validation(file_path: Any) -> Any:
        """Parse issue from file for validation.

        Args:
            file_path: Path to issue file

        Returns:
            Parsed Issue object
        """
        from roadmap.adapters.persistence.parser import IssueParser

        return IssueParser.parse_issue_file(file_path)

    @staticmethod
    def parse_milestone_for_validation(file_path: Any) -> Any:
        """Parse milestone from file for validation.

        Args:
            file_path: Path to milestone file

        Returns:
            Parsed Milestone object
        """
        from roadmap.adapters.persistence.parser import MilestoneParser

        return MilestoneParser.parse_milestone_file(file_path)

    @staticmethod
    def get_parser_module() -> Any:
        """Get the parser module for custom parsing operations.

        Returns:
            Parser module from adapters
        """
        from roadmap.adapters.persistence import parser

        return parser
