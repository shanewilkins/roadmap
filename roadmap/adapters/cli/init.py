"""Initialize a new roadmap directory structure.

This module re-exports the init command from the init package.
The actual implementation is in adapters/cli/init/commands.py
"""

from roadmap.adapters.cli.init.commands import init

__all__ = ["init"]
