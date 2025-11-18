"""Issue management commands.

Commands for creating, listing, updating, and managing issues.
Currently re-exports from roadmap.cli.issue for backward compatibility.

Future: Split into create.py, list.py, update.py, close.py
"""

from roadmap.cli.issue import issue

__all__ = ["issue"]
