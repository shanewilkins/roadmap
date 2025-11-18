"""Project management commands.

Commands for creating and listing projects.
Currently re-exports from roadmap.cli.project for backward compatibility.

Future: Split into create.py, list.py
"""

from roadmap.cli.project import project

__all__ = ["project"]
