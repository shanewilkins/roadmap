"""Gateway to git infrastructure adapter access for core services.

This module mediates all core service access to git integration implementations,
ensuring proper layer separation between Core and Infrastructure.

All imports from roadmap.adapters.git are localized here.
Core services use this gateway instead of importing git infrastructure modules
directly or accessing adapters through them.
"""

from pathlib import Path
from typing import Any


class GitGateway:
    """Gateway for git integration operations.

    Provides a centralized interface for core services to access git
    functionality without direct adapter imports in core.
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
