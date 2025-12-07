"""
DEPRECATED: Use roadmap.shared.formatters instead.

This module is kept for backward compatibility.
All business logic has been moved to shared.formatters.
"""

from roadmap.shared.formatters import KanbanLayout, KanbanOrganizer

__all__ = ["KanbanLayout", "KanbanOrganizer"]
