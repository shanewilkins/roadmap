"""Roadmap CLI - A command line tool for creating and managing roadmaps."""

from importlib.metadata import PackageNotFoundError, version

# Define version BEFORE importing cli modules (they import __version__ from here)
# Keep a source-checkout fallback for direct imports. Installed wheels and sdists
# obtain the authoritative version from their distribution metadata because the
# repository-level pyproject.toml is not part of an installed wheel.
__version__ = "0.1.0"
try:
    __version__ = version("roadmap-cli")
except PackageNotFoundError:
    __version__ = "0.1.0"

# Now import cli (which will import __version__ from this module)
from roadmap.adapters import cli  # noqa: F401, E402

# Legacy exports - use layer-specific imports instead
# from roadmap.core.domain import Issue, Milestone
# from roadmap.adapters.github.github import GitHubClient
# from roadmap.infrastructure.security.credentials import CredentialManager
# from roadmap.core.services import ... etc

__all__ = [
    "__version__",
    "cli",
]
