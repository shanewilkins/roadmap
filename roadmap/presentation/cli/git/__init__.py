"""Git integration commands.

Commands for git hooks and git operations.
Currently re-exports from roadmap.cli.git_integration for backward compatibility.

Future: Move to hooks.py
"""

from roadmap.cli.git_integration import git

__all__ = ["git"]
