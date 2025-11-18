"""Milestone management commands.

Commands for creating, listing, and updating milestones.
Currently re-exports from roadmap.cli.milestone for backward compatibility.

Future: Split into create.py, list.py, update.py
"""

from roadmap.cli.milestone import milestone

__all__ = ["milestone"]
