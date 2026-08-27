"""Roadmap CLI - A command line tool for creating and managing roadmaps."""

from importlib.metadata import PackageNotFoundError, version

# Installed artifacts read their distribution metadata; source checkouts use the
# matching fallback without importing the executable adapter as a side effect.
__version__ = "0.2.0"
try:
    __version__ = version("roadmap-cli")
except PackageNotFoundError:
    __version__ = "0.2.0"

__all__ = ["__version__"]
