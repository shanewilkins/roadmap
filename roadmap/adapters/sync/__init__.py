"""Sync infrastructure for integrating local roadmap with remote repositories.

Provides pluggable backend architecture supporting multiple sync targets.
"""

from .backend_factory import (
    detect_backend_from_config,
    get_backend_for_config,
    get_sync_backend,
)
from .backends import GitHubSyncBackend, VanillaGitSyncBackend
from .generic_sync_orchestrator import GenericSyncOrchestrator

__all__ = [
    "GitHubSyncBackend",
    "VanillaGitSyncBackend",
    "get_sync_backend",
    "get_backend_for_config",
    "detect_backend_from_config",
    "GenericSyncOrchestrator",
]
