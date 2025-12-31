"""Roadmap CLI - A command line tool for creating and managing roadmaps."""

import re
from pathlib import Path

# Define version BEFORE importing cli modules (they import __version__ from here)
# Read version from pyproject.toml to keep a single source of truth
_pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
if _pyproject_path.exists():
    with open(_pyproject_path) as f:
        content = f.read()
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            __version__ = match.group(1)
        else:
            __version__ = "0.0.0"
else:
    __version__ = "0.0.0"

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
