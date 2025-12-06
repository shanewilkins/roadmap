"""Roadmap CLI - A command line tool for creating and managing roadmaps."""

__version__ = "0.6.0"

# Backward compatibility: roadmap.cli -> roadmap.adapters.cli
from roadmap.adapters import cli  # noqa: F401

# Legacy exports - use layer-specific imports instead
# from roadmap.core.domain import Issue, Milestone
# from roadmap.adapters.github.github import GitHubClient
# from roadmap.infrastructure.security.credentials import CredentialManager
# from roadmap.core.services import ... etc

__all__ = [
    "__version__",
    "cli",
]
