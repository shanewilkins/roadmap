"""Sync backend implementations.

Provides pluggable sync backends for integrating with various platforms:
- GitHub: GitHub API-based sync
- Vanilla Git: Git push/pull-based sync
- Other: Extensible for GitLab, Jira, etc.
"""

from .github_sync_backend import GitHubSyncBackend
from .vanilla_git_sync_backend import VanillaGitSyncBackend

__all__ = [
    "GitHubSyncBackend",
    "VanillaGitSyncBackend",
]
