"""
Infrastructure Layer - External System Integration

This layer handles all integration with external systems:
- GitHub API client
- Git repository operations
- Database persistence
- File system operations

Guidelines:
- No business logic here, only system integration
- Each integration is independent
- Can be mocked for testing
- Exposes clean interfaces for other layers

Modules:
- github.py: GitHub API client
- git.py: Git repository operations
- storage.py: Database persistence layer
- persistence.py: State persistence utilities
"""

from .git import GitCommit, GitIntegration
from .github import GitHubAPIError, GitHubClient
from .storage import DatabaseError, StateManager

__all__ = [
    "GitHubClient",
    "GitHubAPIError",
    "GitCommit",
    "GitIntegration",
    "StateManager",
    "DatabaseError",
]
