"""Gateway to validation infrastructure adapter access for core services.

This module mediates core service access to validation-related adapters,
ensuring proper layer separation between Core and Infrastructure.

All imports from roadmap.adapters accessed via validation are localized here.
Core services use this gateway instead of importing validation modules directly
or accessing adapters through validation.
"""

import os
from typing import Any


class _NullGitHubClient:
    """Fallback client for validation when no GitHub token is configured."""

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        return False, "GitHub token not configured"

    def get_team_members(self) -> list[str]:
        return []


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
        from roadmap.infrastructure.security.credentials import get_credential_manager

        resolved_token = token or os.getenv("GITHUB_TOKEN")
        if not resolved_token:
            try:
                resolved_token = get_credential_manager().get_token()
            except Exception:
                resolved_token = None

        if not resolved_token:
            return _NullGitHubClient()

        return GitHubClient(token=resolved_token, owner=org)

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
