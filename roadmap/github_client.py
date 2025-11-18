"""GitHub client module - DEPRECATED.

DEPRECATED: This module is maintained for backward compatibility.
New code should import from roadmap.infrastructure.github instead.

- GitHubClient, GitHubAPIError -> roadmap.infrastructure.github
"""

# Re-export all from infrastructure layer for backward compatibility
from roadmap.infrastructure.github import *  # noqa: F401, F403
from roadmap.infrastructure.github import GitHubAPIError, GitHubClient

__all__ = ["GitHubClient", "GitHubAPIError"]
