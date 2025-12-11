"""
Shared formatting utilities for display and export.

This module consolidates:
- Issue export (JSON, CSV, Markdown)
- Kanban board organization and layout
- Table formatter re-exports (for backward compatibility)

Note: Table formatters (Issue/Project/Milestone) are now in:
- roadmap.shared.formatters.tables.issue_table
- roadmap.shared.formatters.tables.project_table
- roadmap.shared.formatters.tables.milestone_table
"""

# Re-export formatters from their new locations to avoid duplicate code
# and maintain backward compatibility
from roadmap.shared.formatters.export.issue_exporter import IssueExporter
from roadmap.shared.formatters.kanban import KanbanLayout, KanbanOrganizer
from roadmap.shared.formatters.tables import (
    IssueTableFormatter,
    MilestoneTableFormatter,
    ProjectTableFormatter,
)


# ─────────────────────────────────────────────────────────────────────────────
# Kanban Board Organization
# ─────────────────────────────────────────────────────────────────────────────

# Re-export kanban classes from their canonical locations to avoid duplication
# and maintain backward compatibility
from roadmap.shared.formatters.kanban import KanbanLayout, KanbanOrganizer


__all__ = [
    "IssueTableFormatter",
    "ProjectTableFormatter",
    "MilestoneTableFormatter",
    "IssueExporter",
    "KanbanOrganizer",
    "KanbanLayout",
]
